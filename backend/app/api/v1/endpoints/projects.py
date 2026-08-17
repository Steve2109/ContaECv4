"""
ContaEC - Endpoints de Proyectos y Servicios
CRUD de proyectos, tareas, recursos, timesheets y costos con recálculo automático
"""
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_action
from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.company import Company
from app.models.project import (
    Proyecto,
    ProyectoCosto,
    ProyectoEstado,
    ProyectoRecurso,
    ProyectoTarea,
    ProyectoTimesheet,
    TareaEstado,
    TareaPrioridad,
    TipoRecurso,
)
from app.models.user import User
from app.schemas.project import (
    ProyectoCostoCreate,
    ProyectoCostoResponse,
    ProyectoCostoUpdate,
    ProyectoCreate,
    ProyectoRecursoCreate,
    ProyectoRecursoResponse,
    ProyectoRecursoUpdate,
    ProyectoResponse,
    ProyectoStats,
    ProyectoTareaCreate,
    ProyectoTareaResponse,
    ProyectoTareaUpdate,
    ProyectoTimesheetCreate,
    ProyectoTimesheetResponse,
    ProyectoTimesheetUpdate,
    ProyectoUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/projects", tags=["Proyectos y Servicios"])


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


async def _get_proyecto_for_user(
    db: AsyncSession,
    project_id: str,
    user_id: str,
) -> Proyecto:
    """Obtiene un proyecto verificando que pertenezca a una empresa del usuario"""
    result = await db.execute(
        select(Proyecto).where(
            Proyecto.id == project_id,
            Proyecto.is_active == True,
        )
    )
    proyecto = result.scalars().first()
    if not proyecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proyecto no encontrado.",
        )
    await _get_company_for_user(db, proyecto.company_id, user_id)
    return proyecto


# ==========================================
# 1. CRUD Proyectos
# ==========================================

@router.post("", response_model=ProyectoResponse, status_code=status.HTTP_201_CREATED)
async def create_proyecto(
    data: ProyectoCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un nuevo proyecto"""
    data.cliente_id = clean_uuid_param(data.cliente_id, "cliente_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, current_user.id)

    # Validate estado if provided
    if data.estado:
        valid_estados = {e.value for e in ProyectoEstado}
        if data.estado not in valid_estados:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {data.estado}. Debe ser uno de: {', '.join(valid_estados)}",
            )

    proyecto = Proyecto(
        company_id=data.company_id,
        user_id=current_user.id,
        codigo=data.codigo,
        nombre=data.nombre,
        descripcion=data.descripcion,
        cliente_id=data.cliente_id,
        cliente_nombre=data.cliente_nombre,
        estado=data.estado or ProyectoEstado.PLANIFICACION.value,
        fecha_inicio=data.fecha_inicio,
        fecha_fin_estimada=data.fecha_fin_estimada,
        presupuesto=data.presupuesto or Decimal("0"),
        responsable=data.responsable,
        notas=data.notas,
    )

    db.add(proyecto)
    await db.flush()
    # Un proyecto recién creado no tiene tareas/recursos/timesheets/costos;
    # cargar las relaciones explícitamente evita lazy-load asíncrono (MissingGreenlet) al validar.
    proyecto.tareas = []
    proyecto.recursos = []
    proyecto.timesheets = []
    proyecto.costos = []

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="proyecto",
        entity_id=proyecto.id,
        description=f"Proyecto creado: {proyecto.codigo} - {proyecto.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return ProyectoResponse.model_validate(proyecto)


@router.get("", response_model=list[ProyectoResponse])
async def list_proyectos(
    company_id: str | None = None,
    estado: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar proyectos con filtros"""
    company_id = clean_company_id(company_id)
    query = (
        select(Proyecto)
        .join(Company, Proyecto.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(Proyecto.company_id == company_id)
    if estado:
        query = query.where(Proyecto.estado == estado)
    if is_active is not None:
        query = query.where(Proyecto.is_active == is_active)

    query = query.order_by(Proyecto.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    proyectos = result.scalars().all()
    return [ProyectoResponse.model_validate(p) for p in proyectos]


@router.get("/stats", response_model=ProyectoStats)
async def get_proyecto_stats(
    company_id: str = Query(..., description="ID de la empresa"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener estadísticas generales de proyectos"""
    company_id = validate_uuid(company_id, "company_id")
    await _get_company_for_user(db, company_id, current_user.id)

    # Total proyectos
    total_result = await db.execute(
        select(func.count(Proyecto.id)).where(
            Proyecto.company_id == company_id,
            Proyecto.is_active == True,
        )
    )
    total = total_result.scalar() or 0

    # By estado
    planificacion_result = await db.execute(
        select(func.count(Proyecto.id)).where(
            Proyecto.company_id == company_id,
            Proyecto.estado == ProyectoEstado.PLANIFICACION.value,
            Proyecto.is_active == True,
        )
    )
    en_planificacion = planificacion_result.scalar() or 0

    en_progreso_result = await db.execute(
        select(func.count(Proyecto.id)).where(
            Proyecto.company_id == company_id,
            Proyecto.estado == ProyectoEstado.EN_PROGRESO.value,
            Proyecto.is_active == True,
        )
    )
    en_progreso = en_progreso_result.scalar() or 0

    completados_result = await db.execute(
        select(func.count(Proyecto.id)).where(
            Proyecto.company_id == company_id,
            Proyecto.estado == ProyectoEstado.COMPLETADO.value,
            Proyecto.is_active == True,
        )
    )
    completados = completados_result.scalar() or 0

    cancelados_result = await db.execute(
        select(func.count(Proyecto.id)).where(
            Proyecto.company_id == company_id,
            Proyecto.estado == ProyectoEstado.CANCELADO.value,
            Proyecto.is_active == True,
        )
    )
    cancelados = cancelados_result.scalar() or 0

    # Totals
    presupuesto_result = await db.execute(
        select(func.coalesce(func.sum(Proyecto.presupuesto), 0)).where(
            Proyecto.company_id == company_id,
            Proyecto.is_active == True,
        )
    )
    total_presupuesto = presupuesto_result.scalar() or Decimal("0")

    costo_result = await db.execute(
        select(func.coalesce(func.sum(Proyecto.costo_real), 0)).where(
            Proyecto.company_id == company_id,
            Proyecto.is_active == True,
        )
    )
    total_costo_real = costo_result.scalar() or Decimal("0")

    ingreso_result = await db.execute(
        select(func.coalesce(func.sum(Proyecto.ingreso), 0)).where(
            Proyecto.company_id == company_id,
            Proyecto.is_active == True,
        )
    )
    total_ingreso = ingreso_result.scalar() or Decimal("0")

    margen_result = await db.execute(
        select(func.coalesce(func.sum(Proyecto.margen), 0)).where(
            Proyecto.company_id == company_id,
            Proyecto.is_active == True,
        )
    )
    margen_total = margen_result.scalar() or Decimal("0")

    # Total hours from timesheets
    horas_result = await db.execute(
        select(func.coalesce(func.sum(ProyectoTimesheet.horas), 0)).where(
            ProyectoTimesheet.company_id == company_id,
        )
    )
    horas_totales = horas_result.scalar() or Decimal("0")

    return ProyectoStats(
        total_proyectos=total,
        en_planificacion=en_planificacion,
        en_progreso=en_progreso,
        completados=completados,
        cancelados=cancelados,
        total_presupuesto=total_presupuesto,
        total_costo_real=total_costo_real,
        total_ingreso=total_ingreso,
        margen_total=margen_total,
        horas_totales=horas_totales,
    )


@router.get("/{project_id}", response_model=ProyectoResponse)
async def get_proyecto(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un proyecto por ID con todas sus relaciones"""
    project_id = validate_uuid(project_id, "project_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)
    return ProyectoResponse.model_validate(proyecto)


@router.put("/{project_id}", response_model=ProyectoResponse)
async def update_proyecto(
    project_id: str,
    data: ProyectoUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar un proyecto"""
    project_id = validate_uuid(project_id, "project_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    # Validate estado if provided
    if "estado" in update_data and update_data["estado"] is not None:
        valid_estados = {e.value for e in ProyectoEstado}
        if update_data["estado"] not in valid_estados:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {update_data['estado']}",
            )

    for field, value in update_data.items():
        setattr(proyecto, field, value)

    # Recalculate margen if ingreso changed
    if "ingreso" in update_data:
        proyecto.margen = proyecto.ingreso - proyecto.costo_real
        if proyecto.ingreso > 0:
            proyecto.margen_porcentaje = (
                (proyecto.margen / proyecto.ingreso * Decimal("100"))
                .quantize(Decimal("0.01"))
            )
        else:
            proyecto.margen_porcentaje = Decimal("0")

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="proyecto",
        entity_id=proyecto.id,
        description=f"Proyecto actualizado: {proyecto.codigo} - {proyecto.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return ProyectoResponse.model_validate(proyecto)


@router.delete("/{project_id}")
async def delete_proyecto(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un proyecto (soft delete)"""
    project_id = validate_uuid(project_id, "project_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)

    if proyecto.estado == ProyectoEstado.EN_PROGRESO.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar un proyecto en progreso. Cancélelo primero.",
        )

    proyecto.is_active = False
    proyecto.estado = ProyectoEstado.CANCELADO.value
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="proyecto",
        entity_id=proyecto.id,
        description=f"Proyecto eliminado: {proyecto.codigo} - {proyecto.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Proyecto eliminado exitosamente."}


# ==========================================
# 2. CRUD Tareas de Proyecto
# ==========================================

@router.get("/{project_id}/tareas", response_model=list[ProyectoTareaResponse])
async def list_tareas(
    project_id: str,
    estado: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar tareas de un proyecto"""
    project_id = validate_uuid(project_id, "project_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)

    query = (
        select(ProyectoTarea)
        .where(
            ProyectoTarea.proyecto_id == project_id,
            ProyectoTarea.is_active == True,
        )
    )
    if estado:
        query = query.where(ProyectoTarea.estado == estado)

    query = query.order_by(ProyectoTarea.orden, ProyectoTarea.created_at)

    result = await db.execute(query)
    tareas = result.scalars().all()
    return [ProyectoTareaResponse.model_validate(t) for t in tareas]


@router.post("/{project_id}/tareas", response_model=ProyectoTareaResponse, status_code=status.HTTP_201_CREATED)
async def create_tarea(
    project_id: str,
    data: ProyectoTareaCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una tarea en un proyecto"""
    data.employee_id = clean_uuid_param(data.employee_id, "employee_id")
    project_id = validate_uuid(project_id, "project_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)

    # Validate estado if provided
    if data.estado:
        valid_estados = {e.value for e in TareaEstado}
        if data.estado not in valid_estados:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado de tarea inválido: {data.estado}",
            )

    # Validate prioridad if provided
    if data.prioridad:
        valid_prioridades = {p.value for p in TareaPrioridad}
        if data.prioridad not in valid_prioridades:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prioridad inválida: {data.prioridad}",
            )

    tarea = ProyectoTarea(
        proyecto_id=project_id,
        titulo=data.titulo,
        descripcion=data.descripcion,
        estado=data.estado or TareaEstado.PENDIENTE.value,
        prioridad=data.prioridad or TareaPrioridad.MEDIA.value,
        fase=data.fase,
        asignado_a=data.asignado_a,
        employee_id=data.employee_id,
        fecha_inicio=data.fecha_inicio,
        fecha_fin_estimada=data.fecha_fin_estimada,
        horas_estimadas=data.horas_estimadas or Decimal("0"),
        orden=data.orden or 0,
    )

    db.add(tarea)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="proyecto_tarea",
        entity_id=tarea.id,
        description=f"Tarea creada en proyecto {proyecto.codigo}: {tarea.titulo}",
        ip_address=request.client.host if request.client else None,
    )

    return ProyectoTareaResponse.model_validate(tarea)


@router.put("/tareas/{tarea_id}", response_model=ProyectoTareaResponse)
async def update_tarea(
    tarea_id: str,
    data: ProyectoTareaUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una tarea de proyecto"""
    tarea_id = validate_uuid(tarea_id, "tarea_id")
    result = await db.execute(
        select(ProyectoTarea).where(ProyectoTarea.id == tarea_id)
    )
    tarea = result.scalars().first()
    if not tarea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada.",
        )

    # Verify ownership through proyecto
    await _get_proyecto_for_user(db, tarea.proyecto_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    # Validate estado if provided
    if "estado" in update_data and update_data["estado"] is not None:
        valid_estados = {e.value for e in TareaEstado}
        if update_data["estado"] not in valid_estados:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado de tarea inválido: {update_data['estado']}",
            )

    for field, value in update_data.items():
        setattr(tarea, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="proyecto_tarea",
        entity_id=tarea.id,
        description=f"Tarea actualizada: {tarea.titulo}",
        ip_address=request.client.host if request.client else None,
    )

    return ProyectoTareaResponse.model_validate(tarea)


@router.delete("/tareas/{tarea_id}")
async def delete_tarea(
    tarea_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una tarea de proyecto (soft delete)"""
    tarea_id = validate_uuid(tarea_id, "tarea_id")
    result = await db.execute(
        select(ProyectoTarea).where(ProyectoTarea.id == tarea_id)
    )
    tarea = result.scalars().first()
    if not tarea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada.",
        )

    await _get_proyecto_for_user(db, tarea.proyecto_id, current_user.id)

    tarea.is_active = False
    tarea.estado = TareaEstado.CANCELADA.value
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="proyecto_tarea",
        entity_id=tarea_id,
        description=f"Tarea eliminada: {tarea.titulo}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Tarea eliminada exitosamente."}


# ==========================================
# 3. CRUD Recursos de Proyecto
# ==========================================

@router.get("/{project_id}/recursos", response_model=list[ProyectoRecursoResponse])
async def list_recursos(
    project_id: str,
    tipo_recurso: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar recursos de un proyecto"""
    project_id = validate_uuid(project_id, "project_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)

    query = (
        select(ProyectoRecurso)
        .where(
            ProyectoRecurso.proyecto_id == project_id,
            ProyectoRecurso.is_active == True,
        )
    )
    if tipo_recurso:
        query = query.where(ProyectoRecurso.tipo_recurso == tipo_recurso)

    query = query.order_by(ProyectoRecurso.created_at)

    result = await db.execute(query)
    recursos = result.scalars().all()
    return [ProyectoRecursoResponse.model_validate(r) for r in recursos]


@router.post("/{project_id}/recursos", response_model=ProyectoRecursoResponse, status_code=status.HTTP_201_CREATED)
async def create_recurso(
    project_id: str,
    data: ProyectoRecursoCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un recurso en un proyecto"""
    data.employee_id = clean_uuid_param(data.employee_id, "employee_id")
    project_id = validate_uuid(project_id, "project_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)

    # Validate tipo_recurso
    valid_tipos = {t.value for t in TipoRecurso}
    if data.tipo_recurso not in valid_tipos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de recurso inválido: {data.tipo_recurso}. Debe ser uno de: {', '.join(valid_tipos)}",
        )

    costo_unitario = data.costo_unitario or Decimal("0")
    cantidad = data.cantidad or Decimal("1")
    costo_total = costo_unitario * cantidad

    recurso = ProyectoRecurso(
        proyecto_id=project_id,
        tipo_recurso=data.tipo_recurso,
        nombre=data.nombre,
        descripcion=data.descripcion,
        employee_id=data.employee_id,
        costo_unitario=costo_unitario,
        cantidad=cantidad,
        costo_total=costo_total,
        fecha_asignacion=data.fecha_asignacion,
        fecha_liberacion=data.fecha_liberacion,
    )

    db.add(recurso)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="proyecto_recurso",
        entity_id=recurso.id,
        description=f"Recurso asignado a proyecto {proyecto.codigo}: {recurso.nombre} (${costo_total})",
        ip_address=request.client.host if request.client else None,
    )

    return ProyectoRecursoResponse.model_validate(recurso)


@router.put("/recursos/{recurso_id}", response_model=ProyectoRecursoResponse)
async def update_recurso(
    recurso_id: str,
    data: ProyectoRecursoUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar un recurso de proyecto"""
    recurso_id = validate_uuid(recurso_id, "recurso_id")
    result = await db.execute(
        select(ProyectoRecurso).where(ProyectoRecurso.id == recurso_id)
    )
    recurso = result.scalars().first()
    if not recurso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso no encontrado.",
        )

    await _get_proyecto_for_user(db, recurso.proyecto_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(recurso, field, value)

    # Recalculate costo_total if costo_unitario or cantidad changed
    if "costo_unitario" in update_data or "cantidad" in update_data:
        recurso.costo_total = recurso.costo_unitario * recurso.cantidad

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="proyecto_recurso",
        entity_id=recurso.id,
        description=f"Recurso actualizado: {recurso.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return ProyectoRecursoResponse.model_validate(recurso)


@router.delete("/recursos/{recurso_id}")
async def delete_recurso(
    recurso_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un recurso de proyecto (soft delete)"""
    recurso_id = validate_uuid(recurso_id, "recurso_id")
    result = await db.execute(
        select(ProyectoRecurso).where(ProyectoRecurso.id == recurso_id)
    )
    recurso = result.scalars().first()
    if not recurso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurso no encontrado.",
        )

    await _get_proyecto_for_user(db, recurso.proyecto_id, current_user.id)

    recurso.is_active = False
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="proyecto_recurso",
        entity_id=recurso_id,
        description=f"Recurso eliminado: {recurso.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Recurso eliminado exitosamente."}


# ==========================================
# 4. CRUD Timesheets de Proyecto
# ==========================================

@router.get("/{project_id}/timesheets", response_model=list[ProyectoTimesheetResponse])
async def list_timesheets(
    project_id: str,
    employee_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar timesheets de un proyecto"""
    employee_id = clean_uuid_param(employee_id, "employee_id")
    project_id = validate_uuid(project_id, "project_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)

    query = (
        select(ProyectoTimesheet)
        .where(ProyectoTimesheet.proyecto_id == project_id)
    )
    if employee_id:
        query = query.where(ProyectoTimesheet.employee_id == employee_id)

    query = query.order_by(ProyectoTimesheet.fecha.desc())

    result = await db.execute(query)
    timesheets = result.scalars().all()
    return [ProyectoTimesheetResponse.model_validate(t) for t in timesheets]


@router.post("/{project_id}/timesheets", response_model=ProyectoTimesheetResponse, status_code=status.HTTP_201_CREATED)
async def create_timesheet(
    project_id: str,
    data: ProyectoTimesheetCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un registro de timesheet en un proyecto"""
    data.tarea_id = clean_uuid_param(data.tarea_id, "tarea_id")
    data.employee_id = clean_uuid_param(data.employee_id, "employee_id")
    project_id = validate_uuid(project_id, "project_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)

    # Verify company_id matches
    if data.company_id != proyecto.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El company_id no corresponde al proyecto.",
        )

    tarifa_hora = data.tarifa_hora or Decimal("0")
    costo_total = data.horas * tarifa_hora

    timesheet = ProyectoTimesheet(
        company_id=data.company_id,
        proyecto_id=project_id,
        tarea_id=data.tarea_id,
        employee_id=data.employee_id,
        empleado_nombre=data.empleado_nombre,
        fecha=data.fecha,
        horas=data.horas,
        tarifa_hora=tarifa_hora,
        costo_total=costo_total,
        descripcion=data.descripcion,
        es_facturable=data.es_facturable if data.es_facturable is not None else True,
    )

    db.add(timesheet)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="proyecto_timesheet",
        entity_id=timesheet.id,
        description=(
            f"Timesheet registrado en proyecto {proyecto.codigo}: "
            f"{data.empleado_nombre} - {data.horas}h"
        ),
        ip_address=request.client.host if request.client else None,
    )

    return ProyectoTimesheetResponse.model_validate(timesheet)


@router.put("/timesheets/{ts_id}", response_model=ProyectoTimesheetResponse)
async def update_timesheet(
    ts_id: str,
    data: ProyectoTimesheetUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar un registro de timesheet"""
    ts_id = validate_uuid(ts_id, "ts_id")
    result = await db.execute(
        select(ProyectoTimesheet).where(ProyectoTimesheet.id == ts_id)
    )
    timesheet = result.scalars().first()
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet no encontrado.",
        )

    await _get_proyecto_for_user(db, timesheet.proyecto_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(timesheet, field, value)

    # Recalculate costo_total if horas or tarifa_hora changed
    if "horas" in update_data or "tarifa_hora" in update_data:
        timesheet.costo_total = timesheet.horas * timesheet.tarifa_hora

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="proyecto_timesheet",
        entity_id=timesheet.id,
        description=f"Timesheet actualizado: {timesheet.empleado_nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return ProyectoTimesheetResponse.model_validate(timesheet)


@router.delete("/timesheets/{ts_id}")
async def delete_timesheet(
    ts_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un registro de timesheet"""
    ts_id = validate_uuid(ts_id, "ts_id")
    result = await db.execute(
        select(ProyectoTimesheet).where(ProyectoTimesheet.id == ts_id)
    )
    timesheet = result.scalars().first()
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timesheet no encontrado.",
        )

    await _get_proyecto_for_user(db, timesheet.proyecto_id, current_user.id)

    await db.delete(timesheet)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="proyecto_timesheet",
        entity_id=ts_id,
        description=f"Timesheet eliminado: {timesheet.empleado_nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Timesheet eliminado exitosamente."}


# ==========================================
# 5. CRUD Costos de Proyecto
# ==========================================

@router.get("/{project_id}/costos", response_model=list[ProyectoCostoResponse])
async def list_costos(
    project_id: str,
    categoria: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar costos de un proyecto"""
    project_id = validate_uuid(project_id, "project_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)

    query = (
        select(ProyectoCosto)
        .where(ProyectoCosto.proyecto_id == project_id)
    )
    if categoria:
        query = query.where(ProyectoCosto.categoria == categoria)

    query = query.order_by(ProyectoCosto.fecha.desc())

    result = await db.execute(query)
    costos = result.scalars().all()
    return [ProyectoCostoResponse.model_validate(c) for c in costos]


@router.post("/{project_id}/costos", response_model=ProyectoCostoResponse, status_code=status.HTTP_201_CREATED)
async def create_costo(
    project_id: str,
    data: ProyectoCostoCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un costo en un proyecto"""
    data.comprobante_id = clean_uuid_param(data.comprobante_id, "comprobante_id")
    project_id = validate_uuid(project_id, "project_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)

    costo = ProyectoCosto(
        proyecto_id=project_id,
        concepto=data.concepto,
        descripcion=data.descripcion,
        monto=data.monto,
        fecha=data.fecha,
        categoria=data.categoria,
        es_facturable=data.es_facturable if data.es_facturable is not None else False,
        comprobante_id=data.comprobante_id,
    )

    db.add(costo)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="proyecto_costo",
        entity_id=costo.id,
        description=f"Costo registrado en proyecto {proyecto.codigo}: {data.concepto} (${data.monto})",
        ip_address=request.client.host if request.client else None,
    )

    return ProyectoCostoResponse.model_validate(costo)


@router.delete("/costos/{costo_id}")
async def delete_costo(
    costo_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un costo de proyecto"""
    costo_id = validate_uuid(costo_id, "costo_id")
    result = await db.execute(
        select(ProyectoCosto).where(ProyectoCosto.id == costo_id)
    )
    costo = result.scalars().first()
    if not costo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Costo no encontrado.",
        )

    await _get_proyecto_for_user(db, costo.proyecto_id, current_user.id)

    await db.delete(costo)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="proyecto_costo",
        entity_id=costo_id,
        description=f"Costo eliminado: {costo.concepto}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Costo eliminado exitosamente."}


# ==========================================
# 6. Recalcular proyecto
# ==========================================

@router.post("/{project_id}/recalcular", response_model=ProyectoResponse)
async def recalcular_proyecto(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Recalcular costos, márgenes y progreso del proyecto.

    - Suma todos los timesheet costo_total del proyecto
    - Suma todos los ProyectoCosto monto del proyecto
    - Suma todos los ProyectoRecurso costo_total del proyecto
    - Actualiza proyecto.costo_real = timesheets_cost + costos_cost + recursos_cost
    - Actualiza proyecto.margen = proyecto.ingreso - proyecto.costo_real
    - Actualiza proyecto.margen_porcentaje = (margen / ingreso * 100) if ingreso > 0 else 0
    - Calcula proyecto.progreso = promedio de todas las tareas.progreso
    - Actualiza tarea.horas_reales = suma de timesheet horas para esa tarea
    """
    project_id = validate_uuid(project_id, "project_id")
    proyecto = await _get_proyecto_for_user(db, project_id, current_user.id)

    # 1. Sum timesheets costo_total
    ts_cost_result = await db.execute(
        select(func.coalesce(func.sum(ProyectoTimesheet.costo_total), 0)).where(
            ProyectoTimesheet.proyecto_id == project_id,
        )
    )
    timesheets_cost = ts_cost_result.scalar() or Decimal("0")

    # 2. Sum costos monto
    costos_result = await db.execute(
        select(func.coalesce(func.sum(ProyectoCosto.monto), 0)).where(
            ProyectoCosto.proyecto_id == project_id,
        )
    )
    costos_cost = costos_result.scalar() or Decimal("0")

    # 3. Sum recursos costo_total (only active)
    recursos_result = await db.execute(
        select(func.coalesce(func.sum(ProyectoRecurso.costo_total), 0)).where(
            ProyectoRecurso.proyecto_id == project_id,
            ProyectoRecurso.is_active == True,
        )
    )
    recursos_cost = recursos_result.scalar() or Decimal("0")

    # 4. Update proyecto.costo_real
    proyecto.costo_real = (timesheets_cost + costos_cost + recursos_cost).quantize(Decimal("0.01"))

    # 5. Update proyecto.margen
    proyecto.margen = (proyecto.ingreso - proyecto.costo_real).quantize(Decimal("0.01"))

    # 6. Update proyecto.margen_porcentaje
    if proyecto.ingreso > 0:
        proyecto.margen_porcentaje = (
            (proyecto.margen / proyecto.ingreso * Decimal("100"))
            .quantize(Decimal("0.01"))
        )
    else:
        proyecto.margen_porcentaje = Decimal("0")

    # 7. Update tarea.horas_reales for each task
    tareas_result = await db.execute(
        select(ProyectoTarea).where(
            ProyectoTarea.proyecto_id == project_id,
            ProyectoTarea.is_active == True,
        )
    )
    tareas = tareas_result.scalars().all()

    total_progreso = Decimal("0")
    tareas_count = 0

    for tarea in tareas:
        # Sum timesheet horas for this tarea
        tarea_horas_result = await db.execute(
            select(func.coalesce(func.sum(ProyectoTimesheet.horas), 0)).where(
                ProyectoTimesheet.tarea_id == tarea.id,
            )
        )
        tarea.horas_reales = (tarea_horas_result.scalar() or Decimal("0")).quantize(Decimal("0.01"))

        total_progreso += tarea.progreso
        tareas_count += 1

    # 8. Calculate proyecto.progreso = average of all tareas progreso
    if tareas_count > 0:
        proyecto.progreso = (total_progreso / Decimal(str(tareas_count))).quantize(Decimal("0.01"))
    else:
        proyecto.progreso = Decimal("0")

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="RECALCULATE",
        entity_type="proyecto",
        entity_id=proyecto.id,
        description=(
            f"Proyecto recalculado: {proyecto.codigo} - "
            f"costo_real=${proyecto.costo_real}, margen=${proyecto.margen}, "
            f"progreso={proyecto.progreso}%"
        ),
        ip_address=request.client.host if request.client else None,
    )

    # Re-fetch to get updated relationships
    result = await db.execute(
        select(Proyecto).where(Proyecto.id == project_id)
    )
    proyecto = result.scalars().first()

    return ProyectoResponse.model_validate(proyecto)

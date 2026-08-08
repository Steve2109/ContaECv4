"""
ContaEC - Endpoints de Machine Learning / IA
Predicciones, detección de fraude, chatbot, recomendaciones, auto-categorización
"""
import json
import logging
import re
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_action
from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.company import Company
from app.models.ml_ai import (
    ChatbotEstado,
    FraudeEstado,
    FraudeSeveridad,
    MLAlertaFraude,
    MLCategoriaRegla,
    MLChatbotMensaje,
    MLChatbotSesion,
    MLPrediccion,
    MLRecomendacion,
    PrediccionEstado,
    PrediccionTipo,
    RecomendacionEstado,
)
from app.models.user import User
from app.schemas.ml_ai import (
    AlertaFraudeCreate,
    AlertaFraudeResponse,
    AlertaFraudeUpdate,
    CategoriaReglaCreate,
    CategoriaReglaResponse,
    CategoriaReglaUpdate,
    CategorizeRequest,
    CategorizeResponse,
    ChatRequest,
    ChatResponse,
    ChatbotMensajeCreate,
    ChatbotMensajeResponse,
    ChatbotSesionCreate,
    ChatbotSesionResponse,
    MLStats,
    PrediccionCreate,
    PrediccionResponse,
    PrediccionUpdate,
    RecomendacionCreate,
    RecomendacionResponse,
    RecomendacionUpdate,
)
from app.services.ml_service import (
    categorizar,
    chatbot_responder,
    detectar_fraude,
    generar_recomendaciones,
    prediccion_ventas,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ml-ai", tags=["ML / Inteligencia Artificial"])


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
# 1. ESTADÍSTICAS
# ==========================================

@router.get("/stats", response_model=MLStats)
async def get_ml_stats(
    company_id: str = Query(..., description="ID de la empresa"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener estadísticas generales de ML/IA"""
    company_id = validate_uuid(company_id, "company_id")
    await _get_company_for_user(db, company_id, current_user.id)

    # Predicciones
    total_pred = await db.execute(
        select(func.count(MLPrediccion.id)).where(
            MLPrediccion.company_id == company_id,
        )
    )
    pred_completadas = await db.execute(
        select(func.count(MLPrediccion.id)).where(
            MLPrediccion.company_id == company_id,
            MLPrediccion.estado == PrediccionEstado.COMPLETADA.value,
        )
    )
    pred_pendientes = await db.execute(
        select(func.count(MLPrediccion.id)).where(
            MLPrediccion.company_id == company_id,
            MLPrediccion.estado == PrediccionEstado.PENDIENTE.value,
        )
    )

    # Fraude
    total_fraude = await db.execute(
        select(func.count(MLAlertaFraude.id)).where(
            MLAlertaFraude.company_id == company_id,
        )
    )
    fraude_pendientes = await db.execute(
        select(func.count(MLAlertaFraude.id)).where(
            MLAlertaFraude.company_id == company_id,
            MLAlertaFraude.estado == FraudeEstado.PENDIENTE.value,
        )
    )
    fraude_confirmadas = await db.execute(
        select(func.count(MLAlertaFraude.id)).where(
            MLAlertaFraude.company_id == company_id,
            MLAlertaFraude.estado == FraudeEstado.CONFIRMADO.value,
        )
    )
    fraude_criticas = await db.execute(
        select(func.count(MLAlertaFraude.id)).where(
            MLAlertaFraude.company_id == company_id,
            MLAlertaFraude.severidad == FraudeSeveridad.CRITICA.value,
            MLAlertaFraude.estado == FraudeEstado.PENDIENTE.value,
        )
    )

    # Chatbot
    total_sesiones = await db.execute(
        select(func.count(MLChatbotSesion.id)).where(
            MLChatbotSesion.company_id == company_id,
        )
    )
    sesiones_activas = await db.execute(
        select(func.count(MLChatbotSesion.id)).where(
            MLChatbotSesion.company_id == company_id,
            MLChatbotSesion.estado == ChatbotEstado.ACTIVA.value,
        )
    )
    total_mensajes = await db.execute(
        select(func.count(MLChatbotMensaje.id)).where(
            MLChatbotSesion.company_id == company_id,
        ).join(MLChatbotSesion, MLChatbotMensaje.sesion_id == MLChatbotSesion.id)
    )

    # Recomendaciones
    total_rec = await db.execute(
        select(func.count(MLRecomendacion.id)).where(
            MLRecomendacion.company_id == company_id,
        )
    )
    rec_pendientes = await db.execute(
        select(func.count(MLRecomendacion.id)).where(
            MLRecomendacion.company_id == company_id,
            MLRecomendacion.estado == RecomendacionEstado.PENDIENTE.value,
        )
    )
    rec_aplicadas = await db.execute(
        select(func.count(MLRecomendacion.id)).where(
            MLRecomendacion.company_id == company_id,
            MLRecomendacion.estado == RecomendacionEstado.APLICADA.value,
        )
    )

    # Categorización
    total_reglas = await db.execute(
        select(func.count(MLCategoriaRegla.id)).where(
            MLCategoriaRegla.company_id == company_id,
        )
    )
    reglas_activas = await db.execute(
        select(func.count(MLCategoriaRegla.id)).where(
            MLCategoriaRegla.company_id == company_id,
            MLCategoriaRegla.es_activa == True,
        )
    )

    return MLStats(
        total_predicciones=total_pred.scalar() or 0,
        predicciones_completadas=pred_completadas.scalar() or 0,
        predicciones_pendientes=pred_pendientes.scalar() or 0,
        total_alertas_fraude=total_fraude.scalar() or 0,
        alertas_pendientes=fraude_pendientes.scalar() or 0,
        alertas_confirmadas=fraude_confirmadas.scalar() or 0,
        alertas_criticas=fraude_criticas.scalar() or 0,
        total_sesiones_chat=total_sesiones.scalar() or 0,
        sesiones_activas=sesiones_activas.scalar() or 0,
        total_mensajes=total_mensajes.scalar() or 0,
        total_recomendaciones=total_rec.scalar() or 0,
        recomendaciones_pendientes=rec_pendientes.scalar() or 0,
        recomendaciones_aplicadas=rec_aplicadas.scalar() or 0,
        total_reglas=total_reglas.scalar() or 0,
        reglas_activas=reglas_activas.scalar() or 0,
    )


# ==========================================
# 2. PREDICCIONES
# ==========================================

@router.post("/predictions", response_model=PrediccionResponse, status_code=status.HTTP_201_CREATED)
async def create_prediction(
    data: PrediccionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una predicción ML (ejecuta el algoritmo de predicción)"""
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, current_user.id)

    try:
        prediccion = await prediccion_ventas(
            db=db,
            company_id=data.company_id,
            user_id=current_user.id,
            tipo=data.tipo,
            modelo=data.modelo_usado,
        )
    except Exception as e:
        # If prediction fails, create error record
        prediccion = MLPrediccion(
            company_id=data.company_id,
            user_id=current_user.id,
            tipo=data.tipo,
            estado=PrediccionEstado.CON_ERROR.value,
            periodo_desde=data.periodo_desde,
            periodo_hasta=data.periodo_hasta,
            datos_entrada=data.datos_entrada,
            resultado=json.dumps({"error": str(e)}),
            modelo_usado=data.modelo_usado,
        )
        db.add(prediccion)
        await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="ML_PREDICT",
        entity_type="ml_prediccion",
        entity_id=prediccion.id,
        description=f"Predicción {data.tipo} con modelo {data.modelo_usado}: {prediccion.estado}",
        ip_address=request.client.host if request.client else None,
    )

    return PrediccionResponse.model_validate(prediccion)


@router.get("/predictions", response_model=list[PrediccionResponse])
async def list_predictions(
    company_id: str | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar predicciones ML"""
    company_id = clean_company_id(company_id)
    query = (
        select(MLPrediccion)
        .join(Company, MLPrediccion.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(MLPrediccion.company_id == company_id)
    if tipo:
        query = query.where(MLPrediccion.tipo == tipo)
    if estado:
        query = query.where(MLPrediccion.estado == estado)

    query = query.order_by(MLPrediccion.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    predicciones = result.scalars().all()
    return [PrediccionResponse.model_validate(p) for p in predicciones]


@router.get("/predictions/{prediction_id}", response_model=PrediccionResponse)
async def get_prediction(
    prediction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una predicción por ID"""
    prediction_id = validate_uuid(prediction_id, "prediction_id")
    result = await db.execute(
        select(MLPrediccion).where(MLPrediccion.id == prediction_id)
    )
    prediccion = result.scalars().first()
    if not prediccion:
        raise HTTPException(status_code=404, detail="Predicción no encontrada.")
    await _get_company_for_user(db, prediccion.company_id, current_user.id)
    return PrediccionResponse.model_validate(prediccion)


@router.delete("/predictions/{prediction_id}")
async def delete_prediction(
    prediction_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una predicción"""
    prediction_id = validate_uuid(prediction_id, "prediction_id")
    result = await db.execute(
        select(MLPrediccion).where(MLPrediccion.id == prediction_id)
    )
    prediccion = result.scalars().first()
    if not prediccion:
        raise HTTPException(status_code=404, detail="Predicción no encontrada.")
    await _get_company_for_user(db, prediccion.company_id, current_user.id)

    await db.delete(prediccion)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="ml_prediccion",
        entity_id=prediction_id,
        description=f"Predicción eliminada: {prediccion.tipo}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Predicción eliminada exitosamente."}


# ==========================================
# 3. DETECCIÓN DE FRAUDE
# ==========================================

@router.post("/fraud/scan")
async def scan_fraud(
    company_id: str = Query(..., description="ID de la empresa"),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ejecutar escaneo de fraude para una empresa"""
    company_id = validate_uuid(company_id, "company_id")
    await _get_company_for_user(db, company_id, current_user.id)

    try:
        alertas = await detectar_fraude(db=db, company_id=company_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en escaneo de fraude: {str(e)}",
        )

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="ML_FRAUD_SCAN",
        entity_type="ml_alerta_fraude",
        entity_id=company_id,
        description=f"Escaneo de fraude: {len(alertas)} alertas encontradas",
        ip_address=request.client.host if request and request.client else None,
    )

    return {
        "message": f"Escaneo completado. {len(alertas)} alerta(s) encontrada(s).",
        "alertas_count": len(alertas),
        "alertas": [AlertaFraudeResponse.model_validate(a).model_dump() for a in alertas],
    }


@router.get("/fraud/alerts", response_model=list[AlertaFraudeResponse])
async def list_fraud_alerts(
    company_id: str | None = None,
    severidad: str | None = None,
    estado: str | None = None,
    tipo_deteccion: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar alertas de fraude"""
    company_id = clean_company_id(company_id)
    query = (
        select(MLAlertaFraude)
        .join(Company, MLAlertaFraude.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(MLAlertaFraude.company_id == company_id)
    if severidad:
        query = query.where(MLAlertaFraude.severidad == severidad)
    if estado:
        query = query.where(MLAlertaFraude.estado == estado)
    if tipo_deteccion:
        query = query.where(MLAlertaFraude.tipo_deteccion == tipo_deteccion)

    query = query.order_by(MLAlertaFraude.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    alertas = result.scalars().all()
    return [AlertaFraudeResponse.model_validate(a) for a in alertas]


@router.get("/fraud/alerts/{alert_id}", response_model=AlertaFraudeResponse)
async def get_fraud_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una alerta de fraude por ID"""
    alert_id = validate_uuid(alert_id, "alert_id")
    result = await db.execute(
        select(MLAlertaFraude).where(MLAlertaFraude.id == alert_id)
    )
    alerta = result.scalars().first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta de fraude no encontrada.")
    await _get_company_for_user(db, alerta.company_id, current_user.id)
    return AlertaFraudeResponse.model_validate(alerta)


@router.put("/fraud/alerts/{alert_id}", response_model=AlertaFraudeResponse)
async def update_fraud_alert(
    alert_id: str,
    data: AlertaFraudeUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una alerta de fraude (resolver/investigar)"""
    alert_id = validate_uuid(alert_id, "alert_id")
    result = await db.execute(
        select(MLAlertaFraude).where(MLAlertaFraude.id == alert_id)
    )
    alerta = result.scalars().first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta de fraude no encontrada.")
    await _get_company_for_user(db, alerta.company_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alerta, field, value)

    # If estado changed, set resolution date
    if "estado" in update_data and update_data["estado"] in [
        FraudeEstado.CONFIRMADO.value,
        FraudeEstado.DESCARTADO.value,
    ]:
        alerta.resolucion_fecha = datetime.now(timezone.utc)
        if data.resuelto_por is None:
            alerta.resuelto_por = current_user.id

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="ml_alerta_fraude",
        entity_id=alert_id,
        description=f"Alerta fraude actualizada: estado={alerta.estado}",
        ip_address=request.client.host if request.client else None,
    )

    return AlertaFraudeResponse.model_validate(alerta)


# ==========================================
# 4. CHATBOT
# ==========================================

@router.post("/chatbot/sessions", response_model=ChatbotSesionResponse, status_code=status.HTTP_201_CREATED)
async def create_chatbot_session(
    data: ChatbotSesionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una sesión de chatbot"""
    data.company_id = validate_uuid(data.company_id, "company_id")
    try:
        await _get_company_for_user(db, data.company_id, current_user.id)
    except HTTPException:
        raise

    try:
        sesion = MLChatbotSesion(
            company_id=data.company_id,
            user_id=current_user.id,
            estado=ChatbotEstado.ACTIVA.value,
            titulo=data.titulo or "Nueva conversación",
            contexto=json.dumps({"mensajes_count": 0}),
        )

        db.add(sesion)
        await db.flush()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al crear sesión de chatbot: {str(e)}",
        )

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="ml_chatbot_sesion",
        entity_id=sesion.id,
        description=f"Sesión chatbot creada: {sesion.titulo}",
        ip_address=request.client.host if request.client else None,
    )

    return ChatbotSesionResponse.model_validate(sesion)


@router.get("/chatbot/sessions", response_model=list[ChatbotSesionResponse])
async def list_chatbot_sessions(
    company_id: str | None = None,
    estado: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar sesiones del chatbot"""
    company_id = clean_company_id(company_id)
    query = (
        select(MLChatbotSesion)
        .join(Company, MLChatbotSesion.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(MLChatbotSesion.company_id == company_id)
    if estado:
        query = query.where(MLChatbotSesion.estado == estado)

    query = query.order_by(MLChatbotSesion.updated_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    sesiones = result.scalars().all()
    return [ChatbotSesionResponse.model_validate(s) for s in sesiones]


@router.post("/chatbot/chat", response_model=ChatResponse)
async def chat_with_bot(
    data: ChatRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enviar un mensaje al chatbot y recibir respuesta"""
    data.sesion_id = clean_uuid_param(data.sesion_id, "sesion_id")
    # Verify session belongs to user
    result = await db.execute(
        select(MLChatbotSesion).where(MLChatbotSesion.id == data.sesion_id)
    )
    sesion = result.scalars().first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión de chatbot no encontrada.")

    await _get_company_for_user(db, sesion.company_id, current_user.id)

    if sesion.estado == ChatbotEstado.CERRADA.value:
        raise HTTPException(
            status_code=400,
            detail="La sesión de chatbot está cerrada.",
        )

    try:
        assistant_msg = await chatbot_responder(
            db=db,
            sesion_id=data.sesion_id,
            mensaje=data.mensaje,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando mensaje: {str(e)}",
        )

    # Get entities from the assistant message's preceding user message
    user_msg_result = await db.execute(
        select(MLChatbotMensaje).where(
            MLChatbotMensaje.sesion_id == data.sesion_id,
            MLChatbotMensaje.rol == "usuario",
        ).order_by(MLChatbotMensaje.created_at.desc()).limit(1)
    )
    user_msg = user_msg_result.scalars().first()

    entidades_dict = None
    intencion = None
    if user_msg:
        intencion = user_msg.intencion_detectada
        if user_msg.entidades:
            try:
                entidades_dict = json.loads(user_msg.entidades)
            except (json.JSONDecodeError, TypeError):
                pass

    return ChatResponse(
        mensaje_id=assistant_msg.id,
        respuesta=assistant_msg.contenido,
        sesion_id=data.sesion_id,
        intencion_detectada=intencion,
        entidades=entidades_dict,
    )


@router.get("/chatbot/sessions/{session_id}/messages", response_model=list[ChatbotMensajeResponse])
async def get_session_messages(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener mensajes de una sesión del chatbot"""
    session_id = validate_uuid(session_id, "session_id")
    result = await db.execute(
        select(MLChatbotSesion).where(MLChatbotSesion.id == session_id)
    )
    sesion = result.scalars().first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión de chatbot no encontrada.")
    await _get_company_for_user(db, sesion.company_id, current_user.id)

    msg_result = await db.execute(
        select(MLChatbotMensaje)
        .where(MLChatbotMensaje.sesion_id == session_id)
        .order_by(MLChatbotMensaje.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    mensajes = msg_result.scalars().all()
    return [ChatbotMensajeResponse.model_validate(m) for m in mensajes]


@router.delete("/chatbot/sessions/{session_id}")
async def close_chatbot_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cerrar una sesión del chatbot"""
    session_id = validate_uuid(session_id, "session_id")
    result = await db.execute(
        select(MLChatbotSesion).where(MLChatbotSesion.id == session_id)
    )
    sesion = result.scalars().first()
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión de chatbot no encontrada.")
    await _get_company_for_user(db, sesion.company_id, current_user.id)

    sesion.estado = ChatbotEstado.CERRADA.value
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="ml_chatbot_sesion",
        entity_id=session_id,
        description="Sesión chatbot cerrada",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Sesión de chatbot cerrada exitosamente."}


# ==========================================
# 5. RECOMENDACIONES
# ==========================================

@router.post("/recommendations/generate")
async def generate_recommendations(
    company_id: str = Query(..., description="ID de la empresa"),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generar recomendaciones ML para una empresa"""
    company_id = validate_uuid(company_id, "company_id")
    await _get_company_for_user(db, company_id, current_user.id)

    try:
        recomendaciones = await generar_recomendaciones(
            db=db,
            company_id=company_id,
            user_id=current_user.id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando recomendaciones: {str(e)}",
        )

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="ML_RECOMMEND",
        entity_type="ml_recomendacion",
        entity_id=company_id,
        description=f"Recomendaciones generadas: {len(recomendaciones)} nuevas",
        ip_address=request.client.host if request and request.client else None,
    )

    return {
        "message": f"Se generaron {len(recomendaciones)} recomendación(es).",
        "recomendaciones_count": len(recomendaciones),
        "recomendaciones": [
            RecomendacionResponse.model_validate(r).model_dump() for r in recomendaciones
        ],
    }


@router.get("/recommendations", response_model=list[RecomendacionResponse])
async def list_recommendations(
    company_id: str | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar recomendaciones"""
    company_id = clean_company_id(company_id)
    query = (
        select(MLRecomendacion)
        .join(Company, MLRecomendacion.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(MLRecomendacion.company_id == company_id)
    if tipo:
        query = query.where(MLRecomendacion.tipo == tipo)
    if estado:
        query = query.where(MLRecomendacion.estado == estado)

    query = query.order_by(MLRecomendacion.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    recomendaciones = result.scalars().all()
    return [RecomendacionResponse.model_validate(r) for r in recomendaciones]


@router.put("/recommendations/{rec_id}", response_model=RecomendacionResponse)
async def update_recommendation(
    rec_id: str,
    data: RecomendacionUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una recomendación (aplicar/descartar)"""
    rec_id = validate_uuid(rec_id, "rec_id")
    result = await db.execute(
        select(MLRecomendacion).where(MLRecomendacion.id == rec_id)
    )
    rec = result.scalars().first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recomendación no encontrada.")
    await _get_company_for_user(db, rec.company_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rec, field, value)

    # If estado changed to aplicada, set fecha and user
    if "estado" in update_data and update_data["estado"] == RecomendacionEstado.APLICADA.value:
        rec.fecha_aplicacion = datetime.now(timezone.utc)
        if data.aplicada_por is None:
            rec.aplicada_por = current_user.id

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="ml_recomendacion",
        entity_id=rec_id,
        description=f"Recomendación actualizada: estado={rec.estado}",
        ip_address=request.client.host if request.client else None,
    )

    return RecomendacionResponse.model_validate(rec)


@router.delete("/recommendations/{rec_id}")
async def delete_recommendation(
    rec_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una recomendación"""
    rec_id = validate_uuid(rec_id, "rec_id")
    result = await db.execute(
        select(MLRecomendacion).where(MLRecomendacion.id == rec_id)
    )
    rec = result.scalars().first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recomendación no encontrada.")
    await _get_company_for_user(db, rec.company_id, current_user.id)

    await db.delete(rec)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="ml_recomendacion",
        entity_id=rec_id,
        description=f"Recomendación eliminada: {rec.titulo}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Recomendación eliminada exitosamente."}


# ==========================================
# 6. AUTO-CATEGORIZACIÓN (REGLAS)
# ==========================================

@router.get("/categorize/rules", response_model=list[CategoriaReglaResponse])
async def list_category_rules(
    company_id: str = Query(..., description="ID de la empresa"),
    es_activa: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar reglas de categorización"""
    company_id = validate_uuid(company_id, "company_id")
    await _get_company_for_user(db, company_id, current_user.id)

    query = select(MLCategoriaRegla).where(
        MLCategoriaRegla.company_id == company_id,
    )

    if es_activa is not None:
        query = query.where(MLCategoriaRegla.es_activa == es_activa)

    query = query.order_by(MLCategoriaRegla.prioridad.desc(), MLCategoriaRegla.categoria).offset(skip).limit(limit)

    result = await db.execute(query)
    reglas = result.scalars().all()
    return [CategoriaReglaResponse.model_validate(r) for r in reglas]


@router.post("/categorize/rules", response_model=CategoriaReglaResponse, status_code=status.HTTP_201_CREATED)
async def create_category_rule(
    data: CategoriaReglaCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una regla de categorización"""
    data.company_id = validate_uuid(data.company_id, "company_id")
    try:
        await _get_company_for_user(db, data.company_id, current_user.id)
    except HTTPException:
        raise

    # Validate palabras_clave is valid JSON (if provided and non-empty)
    if data.palabras_clave:
        try:
            json.loads(data.palabras_clave)
        except (json.JSONDecodeError, TypeError):
            # If not valid JSON, treat as plain comma-separated words and convert to JSON array
            words = [w.strip() for w in data.palabras_clave.split(",") if w.strip()]
            data.palabras_clave = json.dumps(words)

    # Validate regex if provided (optional - skip on invalid)
    if data.patron_regex:
        try:
            re.compile(data.patron_regex)
        except re.error:
            # Invalid regex - silently clear it rather than rejecting
            data.patron_regex = None

    regla = MLCategoriaRegla(
        company_id=data.company_id,
        categoria=data.categoria,
        subcategoria=data.subcategoria,
        palabras_clave=data.palabras_clave,
        patron_regex=data.patron_regex,
        prioridad=data.prioridad,
        es_activa=data.es_activa,
    )

    db.add(regla)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="ml_categoria_regla",
        entity_id=regla.id,
        description=f"Regla de categorización creada: {regla.categoria}",
        ip_address=request.client.host if request.client else None,
    )

    return CategoriaReglaResponse.model_validate(regla)


@router.put("/categorize/rules/{rule_id}", response_model=CategoriaReglaResponse)
async def update_category_rule(
    rule_id: str,
    data: CategoriaReglaUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una regla de categorización"""
    rule_id = validate_uuid(rule_id, "rule_id")
    result = await db.execute(
        select(MLCategoriaRegla).where(MLCategoriaRegla.id == rule_id)
    )
    regla = result.scalars().first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla de categorización no encontrada.")
    await _get_company_for_user(db, regla.company_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    # Validate palabras_clave if provided
    if "palabras_clave" in update_data and update_data["palabras_clave"]:
        try:
            json.loads(update_data["palabras_clave"])
        except (json.JSONDecodeError, TypeError):
            # If not valid JSON, treat as plain comma-separated words and convert to JSON array
            words = [w.strip() for w in update_data["palabras_clave"].split(",") if w.strip()]
            update_data["palabras_clave"] = json.dumps(words)

    # Validate regex if provided (optional - skip on invalid)
    if "patron_regex" in update_data and update_data["patron_regex"]:
        try:
            re.compile(update_data["patron_regex"])
        except re.error:
            update_data["patron_regex"] = None

    for field, value in update_data.items():
        setattr(regla, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="ml_categoria_regla",
        entity_id=rule_id,
        description=f"Regla de categorización actualizada: {regla.categoria}",
        ip_address=request.client.host if request.client else None,
    )

    return CategoriaReglaResponse.model_validate(regla)


@router.delete("/categorize/rules/{rule_id}")
async def delete_category_rule(
    rule_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una regla de categorización"""
    rule_id = validate_uuid(rule_id, "rule_id")
    result = await db.execute(
        select(MLCategoriaRegla).where(MLCategoriaRegla.id == rule_id)
    )
    regla = result.scalars().first()
    if not regla:
        raise HTTPException(status_code=404, detail="Regla de categorización no encontrada.")
    await _get_company_for_user(db, regla.company_id, current_user.id)

    await db.delete(regla)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="ml_categoria_regla",
        entity_id=rule_id,
        description=f"Regla de categorización eliminada: {regla.categoria}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Regla de categorización eliminada exitosamente."}


@router.post("/categorize/categorize", response_model=CategorizeResponse)
async def categorize_description(
    data: CategorizeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Categorizar una descripción usando las reglas configuradas"""
    await _get_company_for_user(db, data.company_id, current_user.id)

    result = await categorizar(
        db=db,
        company_id=data.company_id,
        descripcion=data.descripcion,
    )

    return CategorizeResponse(
        categoria=result.get("categoria"),
        subcategoria=result.get("subcategoria"),
        confianza=result.get("confianza", Decimal("0")),
        regla_aplicada_id=result.get("regla_aplicada_id"),
        todas_candidatas=result.get("todas_candidatas", []),
    )

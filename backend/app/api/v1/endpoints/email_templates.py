"""
ContaEC - Endpoints de Plantillas de Correo Electrónico
CRUD de plantillas, previsualización y envío de correos con plantillas
"""
import html
import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_action
from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.email_service import EmailServiceError, send_comprobante_email
from app.core.encryption import decrypt_field
from app.core.config import get_settings
from app.core.security import get_current_user
from app.models.comprobante import Comprobante
from app.models.email_template import EmailTemplate
from app.models.user import User, UserConfig
from app.schemas.email_template import (
    EmailSendRequest,
    EmailTemplateCreate,
    EmailTemplateCustomPreviewRequest,
    EmailTemplatePreviewRequest,
    EmailTemplateResponse,
    EmailTemplateUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email-templates", tags=["Plantillas de Correo"])

settings = get_settings()


def _render_template(template_str: str, data: dict[str, str]) -> str:
    """Reemplaza variables {{variable}} en una cadena de texto"""
    def replace_var(match):
        var_name = match.group(1).strip()
        value = data.get(var_name, match.group(0))
        # Security: escape HTML in values to prevent XSS
        return html.escape(str(value))
    return re.sub(r'\{\{(\w+)\}\}', replace_var, template_str)


# ==========================================
# Endpoints CRUD
# ==========================================

@router.post("", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_email_template(
    data: EmailTemplateCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva plantilla de correo electrónico"""
    # Si is_default=True, quitar default de otras plantillas del mismo tipo
    if data.is_default:
        result = await db.execute(
            select(EmailTemplate).where(
                EmailTemplate.user_id == current_user.id,
                EmailTemplate.tipo == data.tipo,
                EmailTemplate.is_default == True,
            )
        )
        for existing in result.scalars().all():
            existing.is_default = False

    template = EmailTemplate(
        user_id=current_user.id,
        nombre=data.nombre,
        tipo=data.tipo,
        asunto=data.asunto,
        cuerpo_html=data.cuerpo_html,
        cuerpo_texto=data.cuerpo_texto,
        is_default=data.is_default,
    )
    db.add(template)
    await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="email_template",
        entity_id=template.id,
        description=f"Plantilla de correo creada: {data.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return EmailTemplateResponse.model_validate(template)


@router.get("", response_model=list[EmailTemplateResponse])
async def list_email_templates(
    tipo: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar plantillas de correo del usuario"""
    query = select(EmailTemplate).where(
        EmailTemplate.user_id == current_user.id,
    )

    if tipo:
        query = query.where(EmailTemplate.tipo == tipo)

    if is_active is not None:
        query = query.where(EmailTemplate.is_active == is_active)

    query = query.order_by(EmailTemplate.tipo, EmailTemplate.nombre).offset(skip).limit(limit)

    result = await db.execute(query)
    templates = result.scalars().all()

    return [EmailTemplateResponse.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=EmailTemplateResponse)
async def get_email_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una plantilla de correo específica"""
    template_id = validate_uuid(template_id, "template_id")
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalars().first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )

    if template.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a esta plantilla.",
        )

    return EmailTemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=EmailTemplateResponse)
async def update_email_template(
    template_id: str,
    data: EmailTemplateUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una plantilla de correo"""
    template_id = validate_uuid(template_id, "template_id")
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalars().first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )

    if template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a esta plantilla.",
        )

    # Si se establece como default, quitar default de otras del mismo tipo
    if data.is_default:
        existing_result = await db.execute(
            select(EmailTemplate).where(
                EmailTemplate.user_id == current_user.id,
                EmailTemplate.tipo == (data.tipo or template.tipo),
                EmailTemplate.is_default == True,
                EmailTemplate.id != template_id,
            )
        )
        for existing in existing_result.scalars().all():
            existing.is_default = False

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="email_template",
        entity_id=template.id,
        description=f"Plantilla actualizada: {template.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return EmailTemplateResponse.model_validate(template)


@router.delete("/{template_id}")
async def delete_email_template(
    template_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Desactivar una plantilla de correo (eliminación lógica)"""
    template_id = validate_uuid(template_id, "template_id")
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalars().first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )

    if template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a esta plantilla.",
        )

    template.is_active = False
    await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="email_template",
        entity_id=template.id,
        description=f"Plantilla desactivada: {template.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Plantilla desactivada exitosamente."}


@router.post("/{template_id}/preview")
async def preview_email_template(
    template_id: str,
    data: EmailTemplatePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Previsualizar una plantilla con datos de ejemplo"""
    template_id = validate_uuid(template_id, "template_id")
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalars().first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )

    if template.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a esta plantilla.",
        )

    preview = {
        "asunto": _render_template(template.asunto, data.sample_data),
        "cuerpo_html": _render_template(template.cuerpo_html, data.sample_data),
    }
    if template.cuerpo_texto:
        preview["cuerpo_texto"] = _render_template(template.cuerpo_texto, data.sample_data)

    return preview


@router.post("/preview")
async def preview_custom_email_template(
    data: EmailTemplateCustomPreviewRequest,
    current_user: User = Depends(get_current_user),
):
    """Previsualizar HTML y asunto sin necesidad de guardar la plantilla"""
    return {
        "rendered_html": _render_template(data.cuerpo_html, data.sample_data),
        "asunto": _render_template(data.asunto, data.sample_data),
    }


@router.post("/send")
async def send_email_with_template(
    data: EmailSendRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enviar un correo electrónico usando una plantilla y un comprobante"""
    data.template_id = clean_uuid_param(data.template_id, "template_id")
    data.comprobante_id = clean_uuid_param(data.comprobante_id, "comprobante_id")
    # Obtener la plantilla
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.id == data.template_id)
    )
    template = result.scalars().first()

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plantilla no encontrada.",
        )

    if template.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a esta plantilla.",
        )

    # Obtener el comprobante
    comp_result = await db.execute(
        select(Comprobante).where(Comprobante.id == data.comprobante_id)
    )
    comprobante = comp_result.scalars().first()

    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )

    # Destinatario
    to_email = data.to_email or comprobante.cliente_email
    if not to_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se encontró correo de destino. Especifique to_email o asegúrese que el comprobante tenga cliente_email.",
        )

    # Obtener configuración SMTP del usuario
    config_result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    user_config = config_result.scalars().first()

    if not user_config or not user_config.smtp_host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tiene configuración SMTP. Configure su servidor de correo primero.",
        )

    # Preparar variables para la plantilla
    template_data = {
        "empresa_razon_social": comprobante.company.razon_social if comprobante.company else "",
        "empresa_ruc": comprobante.company.ruc if comprobante.company else "",
        "cliente_razon_social": comprobante.cliente_razon_social or "",
        "secuencial": comprobante.secuencial,
        "tipo_comprobante": comprobante.tipo_comprobante,
        "total_con_impuestos": str(comprobante.total_con_impuestos),
        "clave_acceso": comprobante.clave_acceso or "",
        "numero_autorizacion": comprobante.numero_autorizacion or "",
    }

    # Renderizar plantilla
    asunto = _render_template(template.asunto, template_data)
    cuerpo_html = _render_template(template.cuerpo_html, template_data)

    # Enviar correo usando el servicio existente
    try:
        result = send_comprobante_email(
            to_email=to_email,
            cliente_razon_social=comprobante.cliente_razon_social or "",
            tipo_comprobante=comprobante.tipo_comprobante,
            secuencial=comprobante.secuencial,
            clave_acceso=comprobante.clave_acceso or "",
            numero_autorizacion=comprobante.numero_autorizacion or "",
            fecha_autorizacion=str(comprobante.fecha_autorizacion) if comprobante.fecha_autorizacion else "",
            empresa_razon_social=comprobante.company.razon_social if comprobante.company else "",
            empresa_ruc=comprobante.company.ruc if comprobante.company else "",
            total_con_impuestos=str(comprobante.total_con_impuestos),
            smtp_host=user_config.smtp_host,
            smtp_port=user_config.smtp_port or 465,
            smtp_user=user_config.smtp_user or "",
            smtp_password_encrypted=user_config.smtp_password or "",
            smtp_ssl=user_config.smtp_ssl,
            xml_content=comprobante.xml_content,
        )
    except EmailServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="SEND",
        entity_type="email_template",
        entity_id=template.id,
        description=f"Correo enviado con plantilla '{template.nombre}' para comprobante {comprobante.secuencial}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": f"Correo enviado exitosamente a {to_email}", "result": result}

"""
ContaEC - Endpoints de Recepción de Correos Electrónicos
Recepción de correos vía IMAP/POP3 usando configuración del usuario
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.validation import clean_company_id, validate_uuid
from app.core.email_receiver import (
    EmailReceiverError,
    download_attachment,
    receive_emails_imap,
    receive_emails_pop3,
)
from app.core.encryption import decrypt_field
from app.core.config import get_settings
from app.core.security import get_current_user
from app.models.user import User, UserConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email", tags=["Recepción de Correo"])

settings = get_settings()


@router.post("/receive")
async def receive_emails(
    protocol: str = "IMAP",
    folder: str = "INBOX",
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Recibir correos electrónicos usando IMAP o POP3.

    Utiliza la configuración de correo del usuario (host, puerto, credenciales).
    """
    # Obtener configuración del usuario
    config_result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    user_config = config_result.scalars().first()

    if not user_config or not user_config.smtp_host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tiene configuración de correo. Configure su servidor primero.",
        )

    # Determinar protocolo y puerto
    protocol = protocol.upper()
    if protocol == "IMAP":
        host = user_config.smtp_host
        port = 993  # Puerto IMAP por defecto con SSL
        use_ssl = user_config.smtp_ssl
    elif protocol == "POP3":
        host = user_config.smtp_host
        port = 995  # Puerto POP3 por defecto con SSL
        use_ssl = user_config.smtp_ssl
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Protocolo no soportado: {protocol}. Use IMAP o POP3.",
        )

    # Descifrar contraseña
    try:
        password = decrypt_field(user_config.smtp_password, settings.ENCRYPTION_KEY)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al descifrar la contraseña de correo.",
        )

    # Recibir correos
    try:
        if protocol == "IMAP":
            emails = await receive_emails_imap(
                host=host,
                port=port,
                user=user_config.smtp_user or current_user.email,
                password=password,
                ssl=use_ssl,
                folder=folder,
                limit=limit,
            )
        else:
            emails = await receive_emails_pop3(
                host=host,
                port=port,
                user=user_config.smtp_user or current_user.email,
                password=password,
                ssl=use_ssl,
                limit=limit,
            )
    except EmailReceiverError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    return {"count": len(emails), "emails": emails}


@router.get("/inbox")
async def get_inbox(
    protocol: str = "IMAP",
    folder: str = "INBOX",
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar correos en la bandeja de entrada.

    Usa la configuración IMAP/POP3 del usuario.
    """
    # Reutiliza la misma lógica de recepción
    config_result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    user_config = config_result.scalars().first()

    if not user_config or not user_config.smtp_host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tiene configuración de correo. Configure su servidor primero.",
        )

    protocol = protocol.upper()
    if protocol == "IMAP":
        host = user_config.smtp_host
        port = 993
        use_ssl = user_config.smtp_ssl
    elif protocol == "POP3":
        host = user_config.smtp_host
        port = 995
        use_ssl = user_config.smtp_ssl
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Protocolo no soportado: {protocol}",
        )

    try:
        password = decrypt_field(user_config.smtp_password, settings.ENCRYPTION_KEY)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al descifrar la contraseña de correo.",
        )

    try:
        if protocol == "IMAP":
            emails = await receive_emails_imap(
                host=host,
                port=port,
                user=user_config.smtp_user or current_user.email,
                password=password,
                ssl=use_ssl,
                folder=folder,
                limit=limit,
            )
        else:
            emails = await receive_emails_pop3(
                host=host,
                port=port,
                user=user_config.smtp_user or current_user.email,
                password=password,
                ssl=use_ssl,
                limit=limit,
            )
    except EmailReceiverError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # Devolver solo resumen (sin adjuntos completos)
    inbox = []
    for e in emails:
        inbox.append({
            "id": e["id"],
            "subject": e["subject"],
            "from": e["from"],
            "date": e["date"],
            "attachments_count": len(e.get("attachments", [])),
            "attachments": [
                {"filename": a["filename"], "content_type": a["content_type"], "size": a["size"]}
                for a in e.get("attachments", [])
            ],
        })

    return {"count": len(inbox), "emails": inbox}


@router.get("/{email_id}/attachments")
async def list_email_attachments(
    email_id: str,
    protocol: str = "IMAP",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar adjuntos de un correo electrónico específico"""
    email_id = validate_uuid(email_id, "email_id")
    # Obtener configuración
    config_result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    user_config = config_result.scalars().first()

    if not user_config or not user_config.smtp_host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tiene configuración de correo.",
        )

    # Obtener correos y buscar el específico
    protocol = protocol.upper()
    host = user_config.smtp_host
    use_ssl = user_config.smtp_ssl
    port = 993 if protocol == "IMAP" else 995

    try:
        password = decrypt_field(user_config.smtp_password, settings.ENCRYPTION_KEY)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al descifrar la contraseña de correo.",
        )

    try:
        if protocol == "IMAP":
            emails = await receive_emails_imap(
                host=host, port=port,
                user=user_config.smtp_user or current_user.email,
                password=password, ssl=use_ssl, limit=100,
            )
        else:
            emails = await receive_emails_pop3(
                host=host, port=port,
                user=user_config.smtp_user or current_user.email,
                password=password, ssl=use_ssl, limit=100,
            )
    except EmailReceiverError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    # Buscar correo específico
    target_email = None
    for e in emails:
        if e["id"] == email_id:
            target_email = e
            break

    if not target_email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Correo no encontrado.",
        )

    return {"email_id": email_id, "attachments": target_email.get("attachments", [])}


@router.get("/{email_id}/attachments/{attachment_index}/download")
async def download_email_attachment(
    email_id: str,
    attachment_index: int,
    protocol: str = "IMAP",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Descargar un adjunto específico de un correo electrónico"""
    email_id = validate_uuid(email_id, "email_id")
    config_result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    user_config = config_result.scalars().first()

    if not user_config or not user_config.smtp_host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tiene configuración de correo.",
        )

    protocol = protocol.upper()
    host = user_config.smtp_host
    use_ssl = user_config.smtp_ssl
    port = 993 if protocol == "IMAP" else 995

    try:
        password = decrypt_field(user_config.smtp_password, settings.ENCRYPTION_KEY)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al descifrar la contraseña de correo.",
        )

    try:
        content = await download_attachment(
            host=host,
            port=port,
            user=user_config.smtp_user or current_user.email,
            password=password,
            email_id=email_id,
            attachment_index=attachment_index,
            protocol=protocol,
            ssl=use_ssl,
        )
    except EmailReceiverError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename=attachment_{attachment_index}"
        },
    )

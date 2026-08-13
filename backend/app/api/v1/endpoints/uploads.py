"""
ContaEC - Endpoints de Subida de Archivos
Manejo seguro de uploads con escaneo de malware (ClamAV + VirusTotal)
"""
import os
import aiofiles
import logging
import hashlib
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.core.scanner import scan_upload, is_any_threat_found
from app.models.user import User, UserConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/uploads", tags=["Archivos"])
settings = get_settings()

# Tipos MIME permitidos por categoría
ALLOWED_MIME_TYPES = {
    "document": [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/csv",
        "text/plain",
    ],
    "image": [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
        "image/bmp",
    ],
    "signature": [
        "application/x-pkcs12",
        "application/pkcs12",
    ],
    "archive": [
        "application/zip",
        "application/x-zip-compressed",
        "application/xml",
        "text/xml",
    ],
}

# Extensiones permitidas
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp",
    ".p12", ".pfx",
    ".zip", ".xml",
}

# Tamaño máximo por tipo (en bytes)
MAX_FILE_SIZES = {
    "signature": 5 * 1024 * 1024,   # 5MB para firmas
    "logo": 2 * 1024 * 1024,        # 2MB para logos
    "document": 20 * 1024 * 1024,   # 20MB para documentos
    "default": 10 * 1024 * 1024,    # 10MB por defecto
}


def _get_file_extension(filename: str) -> str:
    """Obtiene la extensión del archivo en minúsculas"""
    return os.path.splitext(filename)[1].lower() if filename else ""


def _validate_file_type(filename: str, content_type: Optional[str]) -> str:
    """
    Valida el tipo de archivo.
    Returns la categoría del archivo.
    """
    ext = _get_file_extension(filename)

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido: {ext}. "
                   f"Extensiones permitidas: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Determinar categoría
    if ext in (".p12", ".pfx"):
        return "signature"
    elif ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"):
        return "image"
    elif ext in (".zip",):
        return "archive"
    else:
        return "document"


def _compute_file_hash(content: bytes) -> str:
    """Calcula el hash SHA-256 del archivo"""
    return hashlib.sha256(content).hexdigest()


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Query("document", description="Categoría: document, signature, logo, archive"),
    scan: bool = Query(True, description="Escanear archivo con antivirus"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Subir un archivo al servidor con escaneo de malware.
    
    Proceso:
    1. Validar tipo y tamaño del archivo
    2. Escanear con ClamAV (si está disponible)
    3. Escanear con VirusTotal (si el usuario lo activó y está configurado)
    4. Guardar archivo si es limpio
    5. Registrar metadatos del archivo
    
    El archivo se almacena en: ./uploads/{user_id}/{category}/
    Los archivos en almacenamiento volátil se eliminan automáticamente después de su uso.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe tener un nombre.",
        )

    # 1. Validar tipo de archivo
    file_category = _validate_file_type(file.filename, file.content_type)

    # Leer contenido
    content = await file.read()
    file_size = len(content)

    # 2. Validar tamaño
    max_size = MAX_FILE_SIZES.get(category, MAX_FILE_SIZES["default"])
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo excede el tamaño máximo permitido ({max_size // (1024*1024)}MB).",
        )

    # 3. Escaneo de malware
    scan_results = []
    if scan:
        # Verificar si el usuario tiene VirusTotal activado
        use_virustotal = False
        result_config = await db.execute(
            select(UserConfig).where(UserConfig.user_id == current_user.id)
        )
        user_config = result_config.scalars().first()
        if user_config and hasattr(user_config, 'virustotal_enabled'):
            use_virustotal = bool(user_config.virustotal_enabled)

        scan_results = await scan_upload(
            content=content,
            filename=file.filename,
            use_virustotal=use_virustotal,
        )

        # Si se detecta malware, rechazar el archivo
        if is_any_threat_found(scan_results):
            threats = [
                f"{r.scanner}: {r.threat}" for r in scan_results if not r.is_clean
            ]
            logger.warning(
                f"⚠️ ARCHIVO RECHAZADO por malware: {file.filename} - {threats}"
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Archivo rechazado: se detectó malware.",
                    "threats": threats,
                    "filename": file.filename,
                },
            )

    # 4. Guardar archivo
    upload_dir = os.path.join(
        settings.UPLOAD_DIR,
        str(current_user.id),
        category,
    )
    os.makedirs(upload_dir, exist_ok=True)

    # Nombre único basado en timestamp y hash
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    file_hash = _compute_file_hash(content)
    ext = _get_file_extension(file.filename)
    safe_filename = f"{timestamp}_{file_hash[:8]}{ext}"
    file_path = os.path.join(upload_dir, safe_filename)

    # Guardar archivo (async)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # 5. Construir respuesta
    scan_summary = [
        {
            "scanner": r.scanner,
            "is_clean": r.is_clean,
            "details": r.details,
        }
        for r in scan_results
    ] if scan_results else [{"scanner": "none", "is_clean": True, "details": "Escaneo deshabilitado"}]

    logger.info(f"Archivo subido: {file.filename} -> {safe_filename} ({file_size} bytes)")

    return {
        "message": "Archivo subido exitosamente.",
        "filename": file.filename,
        "stored_filename": safe_filename,
        "file_size": file_size,
        "file_hash": file_hash,
        "category": file_category,
        "scan_results": scan_summary,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/validate-signature")
async def validate_digital_signature(
    file: UploadFile = File(...),
    password: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Validar una firma electrónica (.p12/.pfx) sin guardarla.
    
    Verifica:
    - Que el archivo sea un PKCS#12 válido
    - Que la contraseña sea correcta
    - Que el certificado no haya expirado
    - Información del certificado (sujeto, emisor, vigencia)
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe tener un nombre.",
        )

    ext = _get_file_extension(file.filename)
    if ext not in (".p12", ".pfx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser formato .p12 o .pfx",
        )

    content = await file.read()

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no debe exceder 5MB.",
        )

    # Escanear antes de procesar
    scan_results = await scan_upload(content=content, filename=file.filename)
    if is_any_threat_found(scan_results):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Archivo rechazado: se detectó malware en la firma electrónica.",
        )

    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography.x509 import ObjectIdentifier

        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            content, password.encode()
        )

        if not certificate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se encontró certificado en el archivo PKCS#12.",
            )

        # Información del certificado
        now = datetime.now(timezone.utc)
        not_before = certificate.not_valid_before_utc
        not_after = certificate.not_valid_after_utc

        is_valid = not_before <= now <= not_after
        is_expired = now > not_after
        is_not_yet_valid = now < not_before

        # Extraer información del sujeto
        subject = certificate.subject
        issuer = certificate.issuer

        def get_name_attrs(name):
            """Extraer atributos comunes de un X509 Name"""
            attrs = {}
            for attr in name:
                oid = attr.oid.dotted_string
                if oid == "2.5.4.3":  # CN
                    attrs["nombre_comun"] = attr.value
                elif oid == "2.5.4.6":  # C
                    attrs["pais"] = attr.value
                elif oid == "2.5.4.7":  # L
                    attrs["localidad"] = attr.value
                elif oid == "2.5.4.8":  # ST
                    attrs["provincia"] = attr.value
                elif oid == "2.5.4.10":  # O
                    attrs["organizacion"] = attr.value
                elif oid == "2.5.4.11":  # OU
                    attrs["unidad_organizativa"] = attr.value
                elif oid == "2.5.4.97":  # organizationIdentifier
                    attrs["identificador_organizacion"] = attr.value
            return attrs

        # Serial number del certificado
        serial = format(certificate.serial_number, 'x').upper()

        # Días hasta expiración
        days_until_expiry = (not_after - now).days if not_after else None

        # Verificar si es un certificado de firma electrónica del Ecuador
        # (BCE, Security Data, ANF)
        issuer_cn = ""
        for attr in issuer:
            if attr.oid.dotted_string == "2.5.4.3":
                issuer_cn = attr.value
                break

        known_ec_ca = ["BANCO CENTRAL DEL ECUADOR", "SECURITY DATA", "ANF"]
        is_ec_signature = any(ca in issuer_cn.upper() for ca in known_ec_ca)

        return {
            "is_valid": is_valid,
            "is_expired": is_expired,
            "is_not_yet_valid": is_not_yet_valid,
            "is_ec_signature": is_ec_signature,
            "subject": get_name_attrs(subject),
            "issuer": get_name_attrs(issuer),
            "issuer_cn": issuer_cn,
            "serial_number": serial,
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
            "days_until_expiry": days_until_expiry,
            "has_private_key": private_key is not None,
            "additional_certs_count": len(additional_certs) if additional_certs else 0,
            "warnings": _get_signature_warnings(
                is_valid, is_expired, is_not_yet_valid,
                days_until_expiry, is_ec_signature, private_key is None
            ),
        }

    except ValueError as e:
        if "password" in str(e).lower() or "mac" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña incorrecta para la firma electrónica.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Archivo PKCS#12 inválido: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error validando firma electrónica: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al validar la firma electrónica: {str(e)}",
        )


def _get_signature_warnings(
    is_valid: bool,
    is_expired: bool,
    is_not_yet_valid: bool,
    days_until_expiry: Optional[int],
    is_ec_signature: bool,
    no_private_key: bool,
) -> list[str]:
    """Genera advertencias sobre el estado de la firma electrónica"""
    warnings = []

    if is_expired:
        warnings.append("La firma electrónica ha EXPIRADO. No puede ser usada para firmar comprobantes.")
    elif is_not_yet_valid:
        warnings.append("La firma electrónica aún no es válida (fecha de inicio futura).")
    elif days_until_expiry is not None and days_until_expiry <= 30:
        warnings.append(
            f"La firma electrónica expirará en {days_until_expiry} días. "
            "Renueve su firma electrónica a tiempo."
        )

    if not is_ec_signature:
        warnings.append(
            "El certificado no parece ser de una autoridad certificadora ecuatoriana "
            "(BCE, Security Data, ANF). Verifique que sea una firma electrónica válida para el SRI."
        )

    if no_private_key:
        warnings.append("No se encontró la clave privada en el archivo. No se podrá firmar comprobantes.")

    return warnings

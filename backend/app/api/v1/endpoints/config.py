"""
ContaEC - Endpoints de Configuración de Usuario
Firma electrónica, SMTP, modo sandbox/producción, VirusTotal, perfil
"""
import os
import uuid
import logging
import asyncio
import smtplib
import aiofiles
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.validation import clean_company_id, validate_uuid
from app.core.security import get_current_user
from app.core.encryption import encrypt_field, decrypt_field
from app.core.config import get_settings
from app.core.scanner import scan_upload, is_any_threat_found, check_clamav_available, check_virustotal_available
from app.models.user import User, UserConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/config", tags=["Configuración"])
settings = get_settings()


def _check_clamav() -> bool:
    """Verifica disponibilidad de ClamAV con cache de 5 min"""
    return check_clamav_available()


def _remove_old_files(directory: str, keep_path: str | None = None) -> None:
    """
    Elimina archivos huérfanos de un directorio (los que ya no están referenciados).

    Args:
        directory: Directorio a limpiar
        keep_path: Archivo que NO se debe eliminar (el recién subido)
    """
    if not directory or not os.path.isdir(directory):
        return
    for filename in os.listdir(directory):
        full = os.path.join(directory, filename)
        if os.path.isfile(full) and full != keep_path:
            try:
                os.unlink(full)
                logger.info(f"Archivo huérfano eliminado: {full}")
            except OSError as e:
                logger.warning(f"No se pudo eliminar {full}: {e}")


def _check_virustotal() -> bool:
    """Verifica disponibilidad de VirusTotal con cache de 5 min"""
    return check_virustotal_available()


@router.get("/user-config")
async def get_user_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener la configuración completa del usuario actual"""
    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    config = result.scalars().first()

    if not config:
        # Crear configuración por defecto
        config = UserConfig(user_id=current_user.id, environment_mode="sandbox")
        db.add(config)
        await db.flush()

    # ── Fallback a datos de la empresa si UserConfig no tiene firma/logo ──
    from app.models.company import Company
    from app.core.permissions import effective_owner_id
    owner_id = effective_owner_id(current_user)
    comp_result = await db.execute(
        select(Company).where(Company.user_id == owner_id, Company.is_active == True)
    )
    companies_list = comp_result.scalars().all()
    active_company = None
    for c in companies_list:
        if c.firma_electronica_path:
            active_company = c
            break
    if not active_company and companies_list:
        active_company = companies_list[0]

    # Firma: priorizar UserConfig; si esta vacia, usar Company
    signature_path = config.digital_signature_path
    signature_expiry = config.signature_expiry_date

    if not signature_path and active_company and active_company.firma_electronica_path:
        try:
            from app.core.encryption import encrypt_field as _enc
            _base = Path(__file__).resolve().parent.parent.parent.parent.parent
            _src = (_base / active_company.firma_electronica_path.lstrip('/')).resolve()
            if _src.is_file():
                _sig_dir = Path(settings.SIGNATURES_DIR) / str(current_user.id)
                _sig_dir.mkdir(parents=True, exist_ok=True)
                _dest = _sig_dir / f"firma_{datetime.now().strftime('%Y%m%d%H%M%S')}{_src.suffix}"
                import shutil
                shutil.copy2(str(_src), str(_dest))
                config.digital_signature_path = _enc(str(_dest), settings.ENCRYPTION_KEY)
                if active_company.firma_electronica_password:
                    from app.core.encryption import decrypt_field as _dec
                    try:
                        _plain_pw = _dec(active_company.firma_electronica_password, settings.ENCRYPTION_KEY)
                    except Exception:
                        _plain_pw = active_company.firma_electronica_password
                    config.digital_signature_password = _enc(_plain_pw, settings.ENCRYPTION_KEY)
                try:
                    from cryptography.hazmat.primitives.serialization import pkcs12 as _pkcs12
                    _cert_data = _src.read_bytes()
                    _pw = ''
                    if config.digital_signature_password:
                        try:
                            _pw = _dec(config.digital_signature_password, settings.ENCRYPTION_KEY)
                        except Exception:
                            pass
                    if _pw:
                        try:
                            _, _cert, _ = _pkcs12.load_key_and_certificates(_cert_data, _pw.encode())
                            if _cert:
                                config.signature_expiry_date = _cert.not_valid_after_utc
                                signature_expiry = _cert.not_valid_after_utc
                        except Exception:
                            pass
                except Exception:
                    pass
                await db.flush()
                signature_path = config.digital_signature_path
        except Exception as e:
            logger.warning(f"No se pudo sincronizar firma de Company a UserConfig: {e}")

    # Fallback logo: si UserConfig no tiene, usar Company.logo_path
    logo_path = config.company_logo_path
    if not logo_path and active_company and active_company.logo_path:
        logo_path = active_company.logo_path
        config.company_logo_path = logo_path
        await db.flush()

    # Estado de la firma electronica
    signature_status = "none"
    signature_days_left = None
    if signature_path:
        if signature_expiry:
            if signature_expiry > datetime.now(timezone.utc):
                signature_status = "valid"
                signature_days_left = (signature_expiry - datetime.now(timezone.utc)).days
            else:
                signature_status = "expired"
        else:
            signature_status = "uploaded"

    return {
        "id": str(config.id),
        "user_id": str(config.user_id),
        "environment_mode": config.environment_mode,
        "virustotal_enabled": config.virustotal_enabled,
        # Firma digital
        "has_digital_signature": bool(signature_path),
        "has_backup_key": bool(current_user.backup_encryption_key),
        "signature_status": signature_status,
        "signature_expiry_date": signature_expiry.isoformat() if signature_expiry else None,
        "signature_days_left": signature_days_left,
        # SMTP
        "has_smtp_config": bool(config.smtp_host),
        "smtp_host": config.smtp_host,
        "smtp_port": config.smtp_port,
        "smtp_user": config.smtp_user,
        "smtp_ssl": config.smtp_ssl,
        "smtp_protocol": config.smtp_protocol,
        # Logo
        "company_logo_path": logo_path,
        # Perfil
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "phone": current_user.phone,
            "language": current_user.language,
            "theme": current_user.theme,
            "license_type": current_user.license_type,
            "license_start_date": current_user.license_start_date.isoformat() if current_user.license_start_date else None,
            "license_end_date": current_user.license_end_date.isoformat() if current_user.license_end_date else None,
        },
        # Escáneres
        "clamav_available": _check_clamav(),
        "virustotal_available": _check_virustotal(),
    }


@router.get("/signature-info")
async def get_signature_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener información detallada del certificado de firma electrónica almacenado.
    Lee el archivo .p12/.pfx del disco y extrae subject, issuer, serial, vigencia, etc.
    """
    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    config = result.scalars().first()

    if not config or not config.digital_signature_path:
        # Fallback: buscar en la empresa activa
        from app.models.company import Company
        from app.core.permissions import effective_owner_id
        owner_id = effective_owner_id(current_user)
        comp_result = await db.execute(
            select(Company).where(Company.user_id == owner_id, Company.is_active == True)
        )
        active_company = None
        for c in comp_result.scalars().all():
            if c.firma_electronica_path:
                active_company = c
                break
        if not active_company:
            raise HTTPException(status_code=404, detail="No hay firma electrónica registrada.")
        # Leer desde la empresa
        _base = Path(__file__).resolve().parent.parent.parent.parent.parent
        _src = (_base / active_company.firma_electronica_path.lstrip('/')).resolve()
        if not _src.is_file():
            raise HTTPException(status_code=404, detail="Archivo de firma no encontrado.")
        _cert_data = _src.read_bytes()
        _pw = ''
        if active_company.firma_electronica_password:
            try:
                _pw = decrypt_field(active_company.firma_electronica_password, settings.ENCRYPTION_KEY)
            except Exception:
                _pw = active_company.firma_electronica_password
    else:
        try:
            stored_path = decrypt_field(config.digital_signature_path, settings.ENCRYPTION_KEY)
        except Exception:
            raise HTTPException(status_code=404, detail="No se pudo decryptar la ruta de la firma.")
        if not stored_path or not os.path.isfile(stored_path):
            raise HTTPException(status_code=404, detail="Archivo de firma no encontrado en disco.")
        _cert_data = open(stored_path, 'rb').read()
        _pw = ''
        if config.digital_signature_password:
            try:
                _pw = decrypt_field(config.digital_signature_password, settings.ENCRYPTION_KEY)
            except Exception:
                pass

    # Parsear el certificado PKCS#12
    try:
        from cryptography.hazmat.primitives.serialization import pkcs12

        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            _cert_data, _pw.encode() if _pw else b''
        )
        if not certificate:
            raise HTTPException(status_code=400, detail="No se encontró certificado en el archivo.")

        now = datetime.now(timezone.utc)
        not_before = certificate.not_valid_before_utc
        not_after = certificate.not_valid_after_utc
        is_valid = not_before <= now <= not_after
        is_expired = now > not_after
        days_until_expiry = (not_after - now).days if not_after else None

        def get_name_attrs(name):
            attrs = {}
            for attr in name:
                oid = attr.oid.dotted_string
                if oid == "2.5.4.3":
                    attrs["nombre_comun"] = attr.value
                elif oid == "2.5.4.6":
                    attrs["pais"] = attr.value
                elif oid == "2.5.4.7":
                    attrs["localidad"] = attr.value
                elif oid == "2.5.4.8":
                    attrs["provincia"] = attr.value
                elif oid == "2.5.4.10":
                    attrs["organizacion"] = attr.value
                elif oid == "2.5.4.11":
                    attrs["unidad_organizativa"] = attr.value
                elif oid == "2.5.4.97":
                    attrs["identificador_organizacion"] = attr.value
            return attrs

        serial = format(certificate.serial_number, 'x').upper()
        issuer_cn = ""
        for attr in certificate.issuer:
            if attr.oid.dotted_string == "2.5.4.3":
                issuer_cn = attr.value
                break

        known_ec_ca = ["BANCO CENTRAL DEL ECUADOR", "SECURITY DATA", "ANF"]
        is_ec_signature = any(ca in issuer_cn.upper() for ca in known_ec_ca)

        warnings = []
        if is_expired:
            warnings.append("La firma electrónica ha EXPIRADO. No puede ser usada para firmar comprobantes.")
        elif days_until_expiry is not None and days_until_expiry <= 30:
            warnings.append(f"La firma electrónica expirará en {days_until_expiry} días. Renueve su firma a tiempo.")
        if not is_ec_signature:
            warnings.append("El certificado no parece ser de una CA ecuatoriana (BCE, Security Data, ANF).")
        if private_key is None:
            warnings.append("No se encontró la clave privada. No se podrá firmar comprobantes.")

        return {
            "is_valid": is_valid,
            "is_expired": is_expired,
            "is_not_yet_valid": now < not_before,
            "is_ec_signature": is_ec_signature,
            "subject": get_name_attrs(certificate.subject),
            "issuer": get_name_attrs(certificate.issuer),
            "issuer_cn": issuer_cn,
            "serial_number": serial,
            "not_before": not_before.isoformat(),
            "not_after": not_after.isoformat(),
            "days_until_expiry": days_until_expiry,
            "has_private_key": private_key is not None,
            "additional_certs_count": len(additional_certs) if additional_certs else 0,
            "warnings": warnings,
        }
    except HTTPException:
        raise
    except ValueError as e:
        if "password" in str(e).lower() or "mac" in str(e).lower():
            raise HTTPException(status_code=400, detail="Contraseña incorrecta para la firma electrónica.")
        raise HTTPException(status_code=400, detail=f"Archivo PKCS#12 inválido: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer la firma electrónica: {str(e)}")


@router.post("/digital-signature")
async def upload_digital_signature(
    file: UploadFile = File(...),
    password: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Subir firma electrónica (.p12/.pfx) y su clave.
    
    Proceso:
    1. Escaneo de malware
    2. Validación del certificado PKCS#12
    3. Extracción de fecha de expiración
    4. Almacenamiento encriptado
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe tener un nombre.",
        )

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".p12", ".pfx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo de firma electrónica debe ser formato .p12 o .pfx"
        )

    content = await file.read()

    # Verificar tamaño (máximo 5MB)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no debe exceder 5MB."
        )

    # Escaneo de malware
    scan_results = await scan_upload(content=content, filename=file.filename)
    if is_any_threat_found(scan_results):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Archivo rechazado: se detectó malware en la firma electrónica.",
        )

    # Guardar archivo en ubicación segura (fuera del directorio público de uploads)
    upload_dir = os.path.join(settings.SIGNATURES_DIR, str(current_user.id))
    os.makedirs(upload_dir, exist_ok=True)

    # Eliminar firma anterior si existe
    result_config = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    old_config = result_config.scalars().first()

    file_path = os.path.join(upload_dir, f"firma_{datetime.now().strftime('%Y%m%d%H%M%S')}.p12")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Validar certificado y extraer información
    expiry_date = None
    cert_info = {}
    warnings = []

    try:
        from cryptography.hazmat.primitives.serialization import pkcs12

        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            content, password.encode('utf-8')
        )

        if certificate:
            expiry_date = certificate.not_valid_after_utc
            not_before = certificate.not_valid_before_utc
            now = datetime.now(timezone.utc)

            is_valid = not_before <= now <= expiry_date
            days_left = (expiry_date - now).days if expiry_date else None

            # Extraer nombre del sujeto
            subject_cn = ""
            issuer_cn = ""
            for attr in certificate.subject:
                if attr.oid.dotted_string == "2.5.4.3":
                    subject_cn = attr.value
            for attr in certificate.issuer:
                if attr.oid.dotted_string == "2.5.4.3":
                    issuer_cn = attr.value

            known_ec_ca = ["BANCO CENTRAL DEL ECUADOR", "SECURITY DATA", "ANF"]
            is_ec = any(ca in issuer_cn.upper() for ca in known_ec_ca)

            cert_info = {
                "subject_cn": subject_cn,
                "issuer_cn": issuer_cn,
                "is_ec_signature": is_ec,
                "not_before": not_before.isoformat(),
                "not_after": expiry_date.isoformat(),
                "days_until_expiry": days_left,
                "has_private_key": private_key is not None,
            }

            if not is_valid and now > expiry_date:
                warnings.append("La firma electrónica ha EXPIRADO. No podrá firmar comprobantes.")
            elif days_left is not None and days_left <= 30:
                warnings.append(f"La firma electrónica expirará en {days_left} días.")

            if not is_ec:
                warnings.append("El certificado no parece ser de una CA ecuatoriana (BCE, Security Data, ANF).")

            if private_key is None:
                warnings.append("No se encontró clave privada. No se podrá firmar comprobantes.")

    except ValueError as e:
        error_msg = str(e).lower()
        if "password" in error_msg or "mac" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña incorrecta para la firma electrónica.",
            )
        elif "deserialize" in error_msg or "parse" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archivo de firma corrupto o no es un archivo PKCS#12 valido.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al procesar la firma: {str(e)}",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al procesar el archivo de firma. Verifique que sea un archivo .p12 o .pfx valido. ({str(e)})",
        )

    # Guardar configuración encriptada
    if not old_config:
        old_config = UserConfig(user_id=current_user.id)
        db.add(old_config)

    old_config.digital_signature_path = encrypt_field(file_path, settings.ENCRYPTION_KEY)
    old_config.digital_signature_password = encrypt_field(password, settings.ENCRYPTION_KEY)
    old_config.signature_expiry_date = expiry_date

    await db.flush()

    # Sync firma to Company record as well
    from app.models.company import Company
    from app.core.permissions import effective_owner_id
    owner_id = effective_owner_id(current_user)
    comp_result = await db.execute(
        select(Company).where(Company.user_id == owner_id, Company.is_active == True)
    )
    for comp in comp_result.scalars().all():
        if not comp.firma_electronica_path:
            company_upload_dir = os.path.join(settings.UPLOAD_DIR, "companies")
            os.makedirs(company_upload_dir, exist_ok=True)
            company_firma = os.path.join(company_upload_dir, f"firma_{uuid.uuid4().hex}{ext}")
            import shutil as _shutil
            _shutil.copy2(file_path, company_firma)
            comp.firma_electronica_path = f"/uploads/companies/{os.path.basename(company_firma)}"
            comp.firma_electronica_password = encrypt_field(password, settings.ENCRYPTION_KEY)
            await db.flush()
            break

    # Limpiar firmas anteriores (huérfanas) del usuario: solo queda el archivo nuevo
    _remove_old_files(upload_dir, keep_path=file_path)

    return {
        "message": "Firma electrónica cargada exitosamente.",
        "expiry_date": expiry_date.isoformat() if expiry_date else None,
        "is_valid": expiry_date > datetime.now(timezone.utc) if expiry_date else None,
        "days_until_expiry": cert_info.get("days_until_expiry"),
        "cert_info": cert_info,
        "warnings": warnings,
    }


@router.delete("/digital-signature")
async def delete_digital_signature(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Eliminar la firma electrónica del usuario (archivo .p12/.pfx y su contraseña).
    Se eliminan todos los archivos de firma del directorio del usuario.
    """
    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    config = result.scalars().first()

    if not config or not config.digital_signature_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay firma electrónica registrada.",
        )

    # Eliminar el/los archivo(s) de firma del disco
    try:
        stored_path = decrypt_field(config.digital_signature_path, settings.ENCRYPTION_KEY)
    except Exception:
        stored_path = None

    upload_dir = os.path.join(settings.SIGNATURES_DIR, str(current_user.id))
    if stored_path and os.path.isfile(stored_path):
        try:
            os.unlink(stored_path)
            logger.info(f"Firma eliminada: {stored_path}")
        except OSError as e:
            logger.warning(f"No se pudo eliminar la firma {stored_path}: {e}")

    # Eliminar cualquier otro archivo huérfano del directorio de firmas del usuario
    _remove_old_files(upload_dir)
    try:
        os.rmdir(upload_dir)  # Solo elimina el directorio si quedó vacío
    except OSError:
        pass

    config.digital_signature_path = None
    config.digital_signature_password = None
    config.signature_expiry_date = None
    await db.flush()

    logger.info(f"Firma electrónica de {current_user.email} eliminada")

    return {"message": "Firma electrónica eliminada correctamente."}


@router.get("/signature-status")
async def get_signature_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener el estado de la firma electrónica del usuario.
    Verifica vigencia y devuelve información detallada.
    """
    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    config = result.scalars().first()

    if not config or not config.digital_signature_path:
        return {
            "has_signature": False,
            "status": "none",
            "message": "No se ha cargado una firma electrónica.",
        }

    now = datetime.now(timezone.utc)
    status_str = "uploaded"  # Sin info de expiración

    if config.signature_expiry_date:
        if config.signature_expiry_date > now:
            days_left = (config.signature_expiry_date - now).days
            if days_left <= 30:
                status_str = "expiring_soon"
            else:
                status_str = "valid"
        else:
            status_str = "expired"

    return {
        "has_signature": True,
        "status": status_str,
        "expiry_date": config.signature_expiry_date.isoformat() if config.signature_expiry_date else None,
        "days_until_expiry": (config.signature_expiry_date - now).days if config.signature_expiry_date and config.signature_expiry_date > now else None,
        "is_valid": config.signature_expiry_date > now if config.signature_expiry_date else None,
        "warnings": _get_status_warnings(status_str, config.signature_expiry_date),
    }


def _get_status_warnings(status_str: str, expiry_date) -> list[str]:
    """Genera advertencias basadas en el estado de la firma"""
    warnings = []
    now = datetime.now(timezone.utc)

    if status_str == "expired":
        warnings.append("Su firma electrónica ha EXPIRADO. No puede firmar comprobantes electrónicos.")
    elif status_str == "expiring_soon":
        days = (expiry_date - now).days if expiry_date else 0
        warnings.append(f"Su firma electrónica expirará en {days} días. Renueve a tiempo.")
    elif status_str == "uploaded":
        warnings.append("No se pudo verificar la vigencia de la firma. Verifique manualmente.")

    return warnings


@router.put("/virustotal")
async def toggle_virustotal(
    enabled: bool,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Activar o desactivar VirusTotal para el escaneo de archivos del usuario"""
    if enabled and not settings.VIRUSTOTAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VirusTotal no está configurado en el servidor (falta VIRUSTOTAL_API_KEY en el .env). Contacte al administrador.",
        )

    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    config = result.scalars().first()
    if not config:
        config = UserConfig(user_id=current_user.id)
        db.add(config)

    config.virustotal_enabled = enabled
    await db.flush()

    return {
        "message": f"VirusTotal {'activado' if enabled else 'desactivado'} exitosamente.",
        "virustotal_enabled": enabled,
    }


class SMTPConfigRequest(BaseModel):
    """Esquema para configuración SMTP"""
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_protocol: str = "SMTP"
    smtp_ssl: bool = True


@router.post("/smtp")
async def configure_smtp(
    data: SMTPConfigRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Configurar SMTP para envío de correos"""
    if data.smtp_port < 1 or data.smtp_port > 65535:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Puerto SMTP inválido (1-65535).",
        )

    # Use user-provided values directly (no auto-normalization)
    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    config = result.scalars().first()
    if not config:
        config = UserConfig(user_id=current_user.id)
        db.add(config)

    config.smtp_host = data.smtp_host
    config.smtp_port = data.smtp_port
    config.smtp_user = data.smtp_user
    config.smtp_password = encrypt_field(data.smtp_password, settings.ENCRYPTION_KEY)
    config.smtp_protocol = data.smtp_protocol
    config.smtp_ssl = data.smtp_ssl

    await db.flush()

    return {
        "message": "Configuración SMTP guardada exitosamente.",
        "smtp_host": data.smtp_host,
        "smtp_port": data.smtp_port,
        "smtp_user": data.smtp_user,
        "smtp_ssl": data.smtp_ssl,
    }


@router.post("/test-smtp")
async def test_smtp(
    current_user: User = Depends(get_current_user),
    company_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Probar la configuracion SMTP enviando un correo de prueba"""
    company_id = clean_company_id(company_id)
    from app.models.company import Company

    # Try company-level SMTP first if company_id provided
    company_smtp = None
    if company_id:
        try:
            cid = UUID(company_id)
            comp_result = await db.execute(
                select(Company).where(Company.id == cid, Company.user_id == current_user.id)
            )
            comp = comp_result.scalars().first()
            if comp and comp.smtp_host:
                company_smtp = comp
        except Exception:
            pass

    # Fallback to user-level config
    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    user_config = result.scalars().first()

    # Determine which config to use
    smtp_host = company_smtp.smtp_host if company_smtp else (user_config.smtp_host if user_config else None)
    smtp_port = company_smtp.smtp_port if company_smtp else (user_config.smtp_port if user_config else None)
    smtp_user = company_smtp.smtp_user if company_smtp else (user_config.smtp_user if user_config else None)
    smtp_password_enc = company_smtp.smtp_password if company_smtp else (user_config.smtp_password if user_config else None)
    smtp_ssl = company_smtp.smtp_ssl if company_smtp else (user_config.smtp_ssl if user_config else True)

    if not smtp_host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay configuracion SMTP. Configure primero el correo.",
        )

    def _send_test_email():
        from email.mime.text import MIMEText

        smtp_password = decrypt_field(smtp_password_enc, settings.ENCRYPTION_KEY)

        company_name = company_smtp.razon_social if company_smtp else "ContaEC"

        if smtp_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()

        server.login(smtp_user, smtp_password)

        msg = MIMEText(
            f"ContaEC - Prueba de configuracion SMTP exitosa.\n"
            f"\n"
            f"Empresa: {company_name}\n"
            f"Servidor: {smtp_host}:{smtp_port}\n"
            f"\n"
            f"Si recibio este correo, su configuracion es correcta.",
            "plain"
        )
        msg["Subject"] = f"ContaEC - Prueba SMTP ({company_name})"
        msg["From"] = smtp_user
        msg["To"] = current_user.email

        server.sendmail(smtp_user, current_user.email, msg.as_string())
        server.quit()

    try:
        await asyncio.to_thread(_send_test_email)
        return {"message": "Correo de prueba enviado exitosamente."}
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Autenticacion fallida. Verifique usuario y contraseña. Para Gmail, use una 'Contraseña de aplicacion' (no su contraseña normal)."
        )
    except smtplib.SMTPConnectError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo conectar al servidor SMTP ({smtp_host}:{smtp_port}). Verifique host, puerto y que no este bloqueado por firewall."
        )
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Timeout al conectar a {smtp_host}:{smtp_port}. Verifique que el puerto sea correcto."
        )
    except smtplib.SMTPException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error SMTP: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al enviar correo de prueba: {str(e)}"
        )


@router.put("/environment-mode")
async def set_environment_mode(
    mode: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cambiar modo de ambiente (sandbox/producción).
    
    En modo sandbox:
    - Los comprobantes se envían al SRI de pruebas
    - No tienen validez fiscal
    - Ideal para verificar configuración
    
    En modo producción:
    - Los comprobantes se envían al SRI de producción
    - Tienen validez fiscal
    - Requiere firma electrónica válida
    """
    if mode not in ("sandbox", "production"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Modo inválido. Use 'sandbox' o 'production'."
        )

    # Verificar requisitos para producción
    if mode == "production":
        result_config = await db.execute(
            select(UserConfig).where(UserConfig.user_id == current_user.id)
        )
        config = result_config.scalars().first()

        errors = []
        if not config or not config.digital_signature_path:
            errors.append("Se requiere una firma electrónica válida para operar en producción.")

        if config and config.signature_expiry_date and config.signature_expiry_date < datetime.now(timezone.utc):
            errors.append("Su firma electrónica ha expirado. Renuévela antes de cambiar a producción.")

        if errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "No se puede cambiar a producción. Resuelva los siguientes requisitos:",
                    "errors": errors,
                },
            )

    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    config = result.scalars().first()
    if not config:
        config = UserConfig(user_id=current_user.id)
        db.add(config)

    config.environment_mode = mode
    await db.flush()

    return {
        "message": f"Modo cambiado a {'Producción' if mode == 'production' else 'Pruebas (Sandbox)'}.",
        "environment_mode": mode,
        "warning": "Los comprobantes emitidos en producción tienen validez fiscal." if mode == "production" else None,
    }


class ProfileUpdateRequest(BaseModel):
    """Esquema para actualización de perfil del usuario"""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None


@router.put("/profile")
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar datos del perfil del usuario"""
    if data.full_name is not None:
        if len(data.full_name) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre debe tener al menos 2 caracteres.",
            )
        current_user.full_name = data.full_name

    if data.phone is not None:
        current_user.phone = data.phone

    if data.language is not None:
        if data.language not in ("es_EC", "en_US"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idioma no soportado. Opciones: es_EC, en_US",
            )
        current_user.language = data.language

    if data.theme is not None:
        if data.theme not in ("light", "dark", "system"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tema no válido. Opciones: light, dark, system",
            )
        current_user.theme = data.theme

    await db.flush()

    return {
        "message": "Perfil actualizado exitosamente.",
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "full_name": current_user.full_name,
            "phone": current_user.phone,
            "language": current_user.language,
            "theme": current_user.theme,
        },
    }


class BackupKeyRequest(BaseModel):
    """Esquema para clave de encriptación de backups"""
    key: str


@router.post("/backup-key")
async def set_backup_encryption_key(
    data: BackupKeyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Establecer la clave de encriptación de backups (se solicita una sola vez)"""
    if len(data.key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La clave debe tener al menos 8 caracteres."
        )

    current_user.backup_encryption_key = encrypt_field(data.key, settings.ENCRYPTION_KEY)
    await db.flush()

    return {"message": "Clave de backup configurada exitosamente."}


@router.get("/company-logo")
async def get_company_logo(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Descargar el logo de la empresa del usuario actual"""
    from fastapi.responses import FileResponse
    from app.models.company import Company
    from app.core.permissions import effective_owner_id

    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    config = result.scalars().first()
    logo_path = config.company_logo_path if config else None

    if not logo_path:
        owner_id = effective_owner_id(current_user)
        comp_result = await db.execute(
            select(Company).where(Company.user_id == owner_id, Company.is_active == True)
        )
        for c in comp_result.scalars().all():
            if c.logo_path:
                logo_path = c.logo_path
                if config:
                    config.company_logo_path = logo_path
                    await db.flush()
                break

    # Resolve relative paths like "/uploads/companies/..." to absolute
    def _resolve_logo(p: str) -> str:
        if os.path.isfile(p):
            return p
        # Try resolving relative to project root
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        candidates = [
            project_root / p.lstrip('/'),  # /uploads/... → {root}/uploads/...
            Path(settings.UPLOAD_DIR) / p.replace('/uploads/', ''),
        ]
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved.is_file():
                return str(resolved)
        return p  # fallback

    if logo_path:
        logo_path = _resolve_logo(logo_path)

    if not logo_path or not os.path.isfile(logo_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay logo registrado.",
        )

    return FileResponse(
        path=logo_path,
        media_type="image/webp",
        filename=os.path.basename(logo_path),
    )


@router.post("/company-logo")
async def upload_company_logo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Subir logotipo de la empresa (solo .webp, máx. 2MB para no pesar en el servidor)"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext != ".webp":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El logotipo debe ser formato .webp (máx. 2MB). Convierta la imagen a .webp e intente nuevamente."
        )

    content = await file.read()

    # Verificar tamaño (máximo 2MB)
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El logotipo no debe exceder 2MB."
        )

    # Escaneo de malware
    scan_results = await scan_upload(content=content, filename=file.filename or "logo")
    if is_any_threat_found(scan_results):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Archivo rechazado: se detectó malware.",
        )

    upload_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id), "logos")
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "logo.png")[1] if file.filename else ".png"
    file_path = os.path.join(upload_dir, f"logo_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    config = result.scalars().first()
    if not config:
        config = UserConfig(user_id=current_user.id)
        db.add(config)

    config.company_logo_path = file_path
    await db.flush()

    # Sync logo to Company record as well
    from app.models.company import Company
    from app.core.permissions import effective_owner_id
    owner_id = effective_owner_id(current_user)
    comp_result = await db.execute(
        select(Company).where(Company.user_id == owner_id, Company.is_active == True)
    )
    for comp in comp_result.scalars().all():
        if not comp.logo_path:
            comp.logo_path = file_path
            await db.flush()
            break

    # Limpiar logos anteriores (huérfanos) del usuario: solo queda el archivo nuevo
    _remove_old_files(upload_dir, keep_path=file_path)

    return {"message": "Logotipo cargado exitosamente.", "logo_path": file_path}


@router.delete("/company-logo")
async def delete_company_logo(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Eliminar el logo de la empresa del usuario.
    Se eliminan todos los archivos de logo del directorio del usuario.
    """
    result = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    config = result.scalars().first()

    if not config or not config.company_logo_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay logo registrado.",
        )

    # Eliminar el archivo de logo referenciado (y cualquier huérfano del directorio)
    stored_logo = config.company_logo_path
    if stored_logo and os.path.isfile(stored_logo):
        try:
            os.unlink(stored_logo)
            logger.info(f"Logo eliminado: {stored_logo}")
        except OSError as e:
            logger.warning(f"No se pudo eliminar el logo {stored_logo}: {e}")

    logo_dir = os.path.join(settings.UPLOAD_DIR, str(current_user.id), "logos")
    _remove_old_files(logo_dir)
    try:
        os.rmdir(logo_dir)  # Solo elimina el directorio si quedó vacío
    except OSError:
        pass

    config.company_logo_path = None
    await db.flush()

    logger.info(f"Logo de {current_user.email} eliminado")

    return {"message": "Logotipo eliminado correctamente."}


# ==========================================
# Company-level configuration endpoints
# ==========================================

@router.get("/companies/{company_id}")
async def get_company_config(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener la configuracion de una empresa especifica"""
    from app.models.company import Company
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    return {
        "id": str(company.id),
        "ruc": company.ruc,
        "razon_social": company.razon_social,
        "nombre_comercial": company.nombre_comercial,
        "logo_path": company.logo_path,
        "firma_electronica_path": company.firma_electronica_path,
        "correo": company.correo,
        "telefono": company.telefono,
        "smtp_host": company.smtp_host,
        "smtp_port": company.smtp_port,
        "smtp_user": company.smtp_user,
        "smtp_protocol": company.smtp_protocol,
        "smtp_ssl": company.smtp_ssl,
        "environment_mode": company.environment_mode,
        "virustotal_enabled": company.virustotal_enabled,
    }


@router.put("/companies/{company_id}")
async def update_company_config(
    company_id: UUID,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar la configuracion de una empresa especifica"""
    from app.models.company import Company
    result = await db.execute(
        select(Company).where(Company.id == company_id, Company.user_id == current_user.id)
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Update fields if provided
    if "logo_path" in data:
        company.logo_path = data["logo_path"]
    if "firma_electronica_path" in data:
        company.firma_electronica_path = data["firma_electronica_path"]
    if "firma_electronica_password" in data:
        company.firma_electronica_password = encrypt_field(data["firma_electronica_password"], settings.ENCRYPTION_KEY)
    if "correo" in data:
        company.correo = data["correo"]
    if "telefono" in data:
        company.telefono = data["telefono"]
    if "smtp_host" in data:
        company.smtp_host = data["smtp_host"]
    if "smtp_port" in data:
        company.smtp_port = data["smtp_port"]
    if "smtp_user" in data:
        company.smtp_user = data["smtp_user"]
    if "smtp_password" in data:
        company.smtp_password = encrypt_field(data["smtp_password"], settings.ENCRYPTION_KEY)
    if "smtp_protocol" in data:
        company.smtp_protocol = data["smtp_protocol"]
    if "smtp_ssl" in data:
        company.smtp_ssl = data["smtp_ssl"]
    if "environment_mode" in data:
        company.environment_mode = data["environment_mode"]
    if "virustotal_enabled" in data:
        company.virustotal_enabled = data["virustotal_enabled"]

    await db.flush()

    return {"message": "Configuracion de empresa actualizada exitosamente."}


@router.get("/clamav-status")
async def get_clamav_status(
    current_user: User = Depends(get_current_user),
    force: bool = False,
):
    """Verificar disponibilidad de ClamAV (con opcion de forzar re-chequeo)"""
    return {
        "clamav_available": check_clamav_available(force=force),
        "cached": not force,
    }

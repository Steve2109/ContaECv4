"""
ContaEC - Endpoints de Backup y Restauración
Exportación automática a medianoche, restauración, encriptación
"""
import os
import json
import aiofiles
import logging
import asyncio
import hashlib
import base64
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.fernet import Fernet, InvalidToken

from app.core.database import get_db, async_session_factory
from app.core.security import get_current_user
from app.core.encryption import encrypt_field, decrypt_field
from app.core.config import get_settings
from app.models.user import User
from app.models.company import Company
from app.models.client import Client
from app.models.product import Product

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/backup", tags=["Backup"])
settings = get_settings()


# ---------------------------------------------------------------------------
# Utilidades internas de encriptación de backup
# ---------------------------------------------------------------------------

def _derive_fernet_from_user_key(encrypted_user_key: str) -> Fernet:
    """
    Deriva una instancia de Fernet a partir de la clave de backup
    encriptada del usuario (almacenada en backup_encryption_key).
    """
    backup_key = decrypt_field(encrypted_user_key, settings.ENCRYPTION_KEY)
    key_hash = hashlib.sha256(backup_key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_hash)
    return Fernet(fernet_key)


# ---------------------------------------------------------------------------
# Creación de datos de backup
# ---------------------------------------------------------------------------

async def create_backup_data(user_id: str, encryption_key: str) -> dict:
    """Crear datos de backup para un usuario específico"""
    async with async_session_factory() as session:
        # Obtener datos del usuario
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            return None

        # Obtener empresas
        result = await session.execute(
            select(Company).where(Company.user_id == user_id)
        )
        companies = result.scalars().all()

        # Mapear company_id -> ruc para asociar clientes
        company_ruc_map = {str(c.id): c.ruc for c in companies}

        # Obtener clientes
        company_ids = [c.id for c in companies]
        clients_data = []
        if company_ids:
            result = await session.execute(
                select(Client).where(Client.company_id.in_(company_ids))
            )
            clients_data = result.scalars().all()

        # Obtener productos
        products_data = []
        if company_ids:
            result = await session.execute(
                select(Product).where(Product.company_id.in_(company_ids))
            )
            products_data = result.scalars().all()

        backup = {
            "version": "5.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": {
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "language": user.language,
                "theme": user.theme,
                # license_type puede venir como LicenseType (enum) o str plano (VARCHAR en BD)
                "license_type": (
                    user.license_type.value
                    if hasattr(user.license_type, "value")
                    else user.license_type
                ),
            },
            "companies": [
                {
                    "ruc": c.ruc,
                    "razon_social": c.razon_social,
                    "nombre_comercial": c.nombre_comercial,
                    "dir_matriz": c.dir_matriz,
                    "dir_establecimiento": c.dir_establecimiento,
                    "cod_establecimiento": c.cod_establecimiento,
                    "cod_punto_emision": c.cod_punto_emision,
                    "obligado_contabilidad": c.obligado_contabilidad,
                    "tipo_ambiente": c.tipo_ambiente,
                    "contribuyente_especial": c.contribuyente_especial,
                }
                for c in companies
            ],
            "clients": [
                {
                    "company_ruc": company_ruc_map.get(str(c.company_id), ""),
                    "tipo_identificacion": c.tipo_identificacion,
                    "identificacion": c.identificacion,
                    "razon_social": c.razon_social,
                    "direccion": c.direccion,
                    "email": c.email,
                    "telefono": c.telefono,
                }
                for c in clients_data
            ],
            "products": [
                {
                    "company_ruc": company_ruc_map.get(str(p.company_id), ""),
                    "codigo_principal": p.codigo_principal,
                    "codigo_auxiliar": p.codigo_auxiliar,
                    "descripcion": p.descripcion,
                    "tipo": p.tipo,
                    "precio_unitario": str(p.precio_unitario) if p.precio_unitario is not None else None,
                    "iva_codigo": p.iva_codigo,
                    "iva_porcentaje": str(p.iva_porcentaje) if p.iva_porcentaje is not None else None,
                    "ice_codigo": p.ice_codigo,
                    "ice_porcentaje": str(p.ice_porcentaje) if p.ice_porcentaje is not None else None,
                    "unidad_medida": p.unidad_medida,
                    "descuento": str(p.descuento) if p.descuento is not None else None,
                }
                for p in products_data
            ],
        }

        return backup


# ---------------------------------------------------------------------------
# POST /backup/create
# ---------------------------------------------------------------------------

@router.post("/create")
async def create_backup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear backup manual de los datos del usuario"""
    if not current_user.backup_encryption_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe configurar primero su clave de encriptación de backup."
        )

    backup_data = await create_backup_data(str(current_user.id), settings.ENCRYPTION_KEY)
    if not backup_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Encriptar backup con la clave del usuario
    fernet = _derive_fernet_from_user_key(current_user.backup_encryption_key)
    encrypted_data = fernet.encrypt(json.dumps(backup_data).encode())

    # Guardar archivo
    backup_dir = Path(settings.BACKUP_DIR) / str(current_user.id)
    backup_dir.mkdir(parents=True, exist_ok=True)

    filename = f"backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.contaec"
    file_path = backup_dir / filename

    # Guardar archivo encriptado (async)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(encrypted_data)

    logger.info(f"Backup creado para usuario {current_user.email}: {filename}")

    return {
        "message": "Backup creado exitosamente.",
        "filename": filename,
        "size_bytes": len(encrypted_data),
        "timestamp": backup_data["timestamp"],
    }


# ---------------------------------------------------------------------------
# POST /backup/restore
# ---------------------------------------------------------------------------

@router.post("/restore")
async def restore_backup(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restaurar datos desde un archivo de backup encriptado"""
    if not file.filename.endswith('.contaec'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un backup de ContaEC (.contaec)"
        )

    if not current_user.backup_encryption_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe tener configurada su clave de encriptación de backup."
        )

    content = await file.read()

    try:
        fernet = _derive_fernet_from_user_key(current_user.backup_encryption_key)
        decrypted_data = fernet.decrypt(content)
        backup_data = json.loads(decrypted_data.decode())

    except InvalidToken:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Clave de encriptación incorrecta o archivo corrupto."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al restaurar backup: {str(e)}"
        )

    # Contadores de resultado
    companies_created = 0
    companies_updated = 0
    companies_skipped = 0
    clients_created = 0
    clients_updated = 0
    clients_skipped = 0
    products_created = 0
    products_updated = 0
    products_skipped = 0

    user_id = str(current_user.id)

    # ------------------------------------------------------------------
    # 1. Restaurar empresas (match por user_id + RUC)
    # ------------------------------------------------------------------
    # Obtener todas las empresas actuales del usuario para comparar
    result = await db.execute(
        select(Company).where(Company.user_id == user_id)
    )
    existing_companies = result.scalars().all()
    # Mapear RUC -> instancia de Company
    ruc_to_company: dict[str, Company] = {c.ruc: c for c in existing_companies}
    # Mapear RUC -> id (para asociar clientes después)
    ruc_to_id: dict[str, str] = {c.ruc: str(c.id) for c in existing_companies}

    for comp_data in backup_data.get("companies", []):
        ruc = comp_data.get("ruc")
        if not ruc:
            continue

        existing = ruc_to_company.get(ruc)

        if existing is None:
            # Crear nueva empresa
            new_company = Company(
                id=str(uuid4()),
                user_id=user_id,
                ruc=ruc,
                razon_social=comp_data.get("razon_social", ""),
                nombre_comercial=comp_data.get("nombre_comercial"),
                dir_matriz=comp_data.get("dir_matriz", ""),
                dir_establecimiento=comp_data.get("dir_establecimiento"),
                cod_establecimiento=comp_data.get("cod_establecimiento", "001"),
                cod_punto_emision=comp_data.get("cod_punto_emision", "001"),
                obligado_contabilidad=comp_data.get("obligado_contabilidad", "NO"),
                tipo_ambiente=comp_data.get("tipo_ambiente", "1"),
                contribuyente_especial=comp_data.get("contribuyente_especial"),
            )
            db.add(new_company)
            await db.flush()

            ruc_to_company[ruc] = new_company
            ruc_to_id[ruc] = str(new_company.id)
            companies_created += 1
            logger.info(f"Empresa restaurada (creada): RUC {ruc}")
        else:
            # Verificar si hay cambios y actualizar
            changed = False
            field_map = {
                "razon_social": "razon_social",
                "nombre_comercial": "nombre_comercial",
                "dir_matriz": "dir_matriz",
                "dir_establecimiento": "dir_establecimiento",
                "cod_establecimiento": "cod_establecimiento",
                "cod_punto_emision": "cod_punto_emision",
                "obligado_contabilidad": "obligado_contabilidad",
                "tipo_ambiente": "tipo_ambiente",
                "contribuyente_especial": "contribuyente_especial",
            }
            for backup_field, model_field in field_map.items():
                backup_val = comp_data.get(backup_field)
                current_val = getattr(existing, model_field, None)
                # Normalizar None vs cadena vacía para comparación
                backup_norm = backup_val if backup_val is not None else ""
                current_norm = current_val if current_val is not None else ""
                if backup_norm != current_norm:
                    setattr(existing, model_field, backup_val)
                    changed = True

            if changed:
                companies_updated += 1
                logger.info(f"Empresa restaurada (actualizada): RUC {ruc}")
            else:
                companies_skipped += 1

    # ------------------------------------------------------------------
    # 2. Restaurar clientes (match por company_id + identificacion)
    # ------------------------------------------------------------------
    for client_data in backup_data.get("clients", []):
        company_ruc = client_data.get("company_ruc", "")
        identificacion = client_data.get("identificacion", "")

        if not company_ruc or not identificacion:
            # No se puede asociar el cliente sin empresa o sin identificación
            clients_skipped += 1
            continue

        company_id = ruc_to_id.get(company_ruc)
        if not company_id:
            # La empresa del cliente no existe ni en el backup ni en la BD
            clients_skipped += 1
            continue

        # Buscar cliente existente por company_id + identificacion
        result = await db.execute(
            select(Client).where(
                and_(
                    Client.company_id == company_id,
                    Client.identificacion == identificacion,
                )
            )
        )
        existing_client = result.scalars().first()

        if existing_client is None:
            # Crear nuevo cliente
            new_client = Client(
                id=str(uuid4()),
                company_id=company_id,
                tipo_identificacion=client_data.get("tipo_identificacion", "07"),
                identificacion=identificacion,
                razon_social=client_data.get("razon_social", ""),
                direccion=client_data.get("direccion"),
                email=client_data.get("email"),
                telefono=client_data.get("telefono"),
            )
            db.add(new_client)
            clients_created += 1
        else:
            # Verificar si hay cambios y actualizar
            changed = False
            client_field_map = {
                "tipo_identificacion": "tipo_identificacion",
                "razon_social": "razon_social",
                "direccion": "direccion",
                "email": "email",
                "telefono": "telefono",
            }
            for backup_field, model_field in client_field_map.items():
                backup_val = client_data.get(backup_field)
                current_val = getattr(existing_client, model_field, None)
                backup_norm = backup_val if backup_val is not None else ""
                current_norm = current_val if current_val is not None else ""
                if backup_norm != current_norm:
                    setattr(existing_client, model_field, backup_val)
                    changed = True

            if changed:
                clients_updated += 1
            else:
                clients_skipped += 1

    # ------------------------------------------------------------------
    # 3. Restaurar productos (match por company_id + codigo_principal)
    # ------------------------------------------------------------------
    for prod_data in backup_data.get("products", []):
        company_ruc = prod_data.get("company_ruc", "")
        codigo_principal = prod_data.get("codigo_principal", "")

        if not company_ruc or not codigo_principal:
            # No se puede asociar el producto sin empresa o sin código
            products_skipped += 1
            continue

        company_id = ruc_to_id.get(company_ruc)
        if not company_id:
            # La empresa del producto no existe ni en el backup ni en la BD
            products_skipped += 1
            continue

        # Buscar producto existente por company_id + codigo_principal
        result = await db.execute(
            select(Product).where(
                and_(
                    Product.company_id == company_id,
                    Product.codigo_principal == codigo_principal,
                )
            )
        )
        existing_product = result.scalars().first()

        if existing_product is None:
            # Crear nuevo producto
            new_product = Product(
                id=str(uuid4()),
                company_id=company_id,
                codigo_principal=codigo_principal,
                codigo_auxiliar=prod_data.get("codigo_auxiliar"),
                descripcion=prod_data.get("descripcion", ""),
                tipo=prod_data.get("tipo", "B"),
                precio_unitario=Decimal(prod_data["precio_unitario"]) if prod_data.get("precio_unitario") else Decimal("0"),
                iva_codigo=prod_data.get("iva_codigo", "2"),
                iva_porcentaje=Decimal(prod_data["iva_porcentaje"]) if prod_data.get("iva_porcentaje") else Decimal("0"),
                ice_codigo=prod_data.get("ice_codigo"),
                ice_porcentaje=Decimal(prod_data["ice_porcentaje"]) if prod_data.get("ice_porcentaje") else None,
                unidad_medida=prod_data.get("unidad_medida", "Unidad"),
                descuento=Decimal(prod_data["descuento"]) if prod_data.get("descuento") else Decimal("0"),
            )
            db.add(new_product)
            products_created += 1
        else:
            # Verificar si hay cambios y actualizar
            changed = False
            product_field_map = {
                "codigo_auxiliar": "codigo_auxiliar",
                "descripcion": "descripcion",
                "tipo": "tipo",
                "iva_codigo": "iva_codigo",
                "unidad_medida": "unidad_medida",
                "ice_codigo": "ice_codigo",
            }
            for backup_field, model_field in product_field_map.items():
                backup_val = prod_data.get(backup_field)
                current_val = getattr(existing_product, model_field, None)
                backup_norm = backup_val if backup_val is not None else ""
                current_norm = current_val if current_val is not None else ""
                if backup_norm != current_norm:
                    setattr(existing_product, model_field, backup_val)
                    changed = True

            # Campos numéricos (Decimal): comparar como string para evitar
            # diferencias de precisión
            numeric_fields = {
                "precio_unitario": "precio_unitario",
                "iva_porcentaje": "iva_porcentaje",
                "ice_porcentaje": "ice_porcentaje",
                "descuento": "descuento",
            }
            for backup_field, model_field in numeric_fields.items():
                backup_str = prod_data.get(backup_field)
                if backup_str is None:
                    continue
                current_val = getattr(existing_product, model_field, None)
                current_str = str(current_val) if current_val is not None else None
                if backup_str != current_str:
                    try:
                        setattr(existing_product, model_field, Decimal(backup_str))
                        changed = True
                    except Exception:
                        pass  # Ignorar valores numéricos inválidos

            if changed:
                products_updated += 1
            else:
                products_skipped += 1

    # Confirmar todos los cambios en la base de datos
    await db.flush()

    logger.info(
        f"Backup restaurado para {current_user.email}: "
        f"empresas({companies_created} creadas, {companies_updated} actualizadas, {companies_skipped} sin cambios), "
        f"clientes({clients_created} creados, {clients_updated} actualizados, {clients_skipped} sin cambios), "
        f"productos({products_created} creados, {products_updated} actualizados, {products_skipped} sin cambios)"
    )

    return {
        "message": "Backup restaurado exitosamente.",
        "backup_version": backup_data.get("version"),
        "backup_timestamp": backup_data.get("timestamp"),
        "companies": {
            "total_in_backup": len(backup_data.get("companies", [])),
            "created": companies_created,
            "updated": companies_updated,
            "skipped": companies_skipped,
        },
        "clients": {
            "total_in_backup": len(backup_data.get("clients", [])),
            "created": clients_created,
            "updated": clients_updated,
            "skipped": clients_skipped,
        },
        "products": {
            "total_in_backup": len(backup_data.get("products", [])),
            "created": products_created,
            "updated": products_updated,
            "skipped": products_skipped,
        },
    }


# ---------------------------------------------------------------------------
# GET /backup/download/{filename}
# ---------------------------------------------------------------------------

@router.get("/download/{filename}")
async def download_backup(
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """Descargar un archivo de backup encriptado del usuario autenticado"""
    # Prevenir path traversal: solo permitir nombres de archivo simples
    safe_name = Path(filename).name
    if safe_name != filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de archivo inválido."
        )

    if not filename.endswith(".contaec"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un backup de ContaEC (.contaec)"
        )

    # Ruta del archivo dentro del directorio del usuario
    file_path = Path(settings.BACKUP_DIR) / str(current_user.id) / filename

    # Verificar que el archivo existe
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archivo de backup no encontrado."
        )

    # Verificar que la ruta resuelta sigue dentro del directorio del usuario
    backup_dir = Path(settings.BACKUP_DIR) / str(current_user.id)
    try:
        file_path.resolve().relative_to(backup_dir.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado al archivo."
        )

    logger.info(f"Backup descargado por {current_user.email}: {filename}")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


# ---------------------------------------------------------------------------
# GET /backup/list
# ---------------------------------------------------------------------------

@router.get("/list")
async def list_backups(
    current_user: User = Depends(get_current_user),
):
    """Listar backups disponibles del usuario"""
    backup_dir = Path(settings.BACKUP_DIR) / str(current_user.id)
    if not backup_dir.exists():
        return {"backups": []}

    backups = []
    for f in backup_dir.glob("*.contaec"):
        stat = f.stat()
        backups.append({
            "filename": f.name,
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
        })

    return {"backups": sorted(backups, key=lambda x: x["created_at"], reverse=True)}


# ---------------------------------------------------------------------------
# Tarea programada: backup automático a medianoche
# ---------------------------------------------------------------------------

async def midnight_backup_task():
    """Tarea programada para crear backups automáticos a medianoche (Ecuador time UTC-5)"""
    from zoneinfo import ZoneInfo
    
    ecuador_tz = ZoneInfo("America/Guayaquil")  # UTC-5
    
    while True:
        now_utc = datetime.now(timezone.utc)
        now_ecuador = now_utc.astimezone(ecuador_tz)
        
        # Calcular segundos hasta la próxima medianoche (hora Ecuador)
        target = now_ecuador.replace(hour=0, minute=0, second=0, microsecond=0)
        if now_ecuador >= target:
            # Usar timedelta para avanzar al día siguiente
            target = target + timedelta(days=1)

        wait_seconds = (target - now_ecuador).total_seconds()
        await asyncio.sleep(wait_seconds)

        # Ejecutar backup para todos los usuarios activos con clave configurada
        async with async_session_factory() as session:
            result = await session.execute(
                select(User).where(
                    User.is_active == True,
                    User.backup_encryption_key != None,
                )
            )
            users = result.scalars().all()

            for user in users:
                try:
                    backup_data = await create_backup_data(str(user.id), settings.ENCRYPTION_KEY)
                    if backup_data:
                        # Guardar backup automático
                        backup_dir = Path(settings.BACKUP_DIR) / str(user.id)
                        backup_dir.mkdir(parents=True, exist_ok=True)

                        filename = f"auto_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.contaec"
                        file_path = backup_dir / filename

                        # Encriptar con clave del usuario
                        fernet = _derive_fernet_from_user_key(user.backup_encryption_key)
                        encrypted_data = fernet.encrypt(json.dumps(backup_data).encode())

                        # Guardar backup automático (async)
                        async with aiofiles.open(file_path, "wb") as f:
                            await f.write(encrypted_data)

                        logger.info(f"Backup automático creado para {user.email}")

                        # Eliminar backups automáticos mayores a 30 días
                        cutoff = datetime.now(timezone.utc).timestamp() - (30 * 24 * 3600)
                        for old_file in backup_dir.glob("auto_backup_*.contaec"):
                            if old_file.stat().st_ctime < cutoff:
                                old_file.unlink()
                except Exception as e:
                    logger.error(f"Error en backup automático para {user.email}: {e}")

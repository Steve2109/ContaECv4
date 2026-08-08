"""
ContaEC - Endpoints de Proveedores
CRUD de proveedores para facturación electrónica
con tipos de identificación según catálogos del SRI (Tabla 7)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_action
from app.core.database import get_db
from app.core.validation import clean_company_id, validate_uuid
from app.core.security import get_current_user
from app.models.company import Company
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.supplier import SupplierCreate, SupplierResponse, SupplierUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/suppliers", tags=["Proveedores"])


# ==========================================
# Funciones auxiliares
# ==========================================

async def _get_company_for_user(
    db: AsyncSession,
    company_id: str,
    user_id: str,
) -> Company:
    """
    Obtiene una empresa verificando que pertenezca al usuario actual.

    Raises:
        HTTPException: Si la empresa no existe o no pertenece al usuario
    """
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
# Endpoints CRUD
# ==========================================

@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(
    data: SupplierCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crear un nuevo proveedor para una empresa del usuario.

    Verifica que la empresa pertenezca al usuario antes de crear el proveedor.
    """
    data.company_id = validate_uuid(data.company_id, "company_id")
    # Verificar que la empresa pertenece al usuario
    await _get_company_for_user(db, data.company_id, current_user.id)

    # Verificar que no exista un proveedor con la misma identificación en la empresa
    result = await db.execute(
        select(Supplier).where(
            Supplier.company_id == data.company_id,
            Supplier.identificacion == data.identificacion,
            Supplier.is_active == True,
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un proveedor con la identificación '{data.identificacion}' en esta empresa.",
        )

    # Crear proveedor
    supplier = Supplier(
        company_id=data.company_id,
        tipo_identificacion=data.tipo_identificacion,
        identificacion=data.identificacion,
        razon_social=data.razon_social,
        nombre_comercial=data.nombre_comercial,
        direccion=data.direccion,
        email=data.email,
        telefono=data.telefono,
        contacto_nombre=data.contacto_nombre,
        contacto_telefono=data.contacto_telefono,
        forma_pago_habitual=data.forma_pago_habitual,
        plazo_credito_dias=data.plazo_credito_dias,
        retencion_iva_codigo=data.retencion_iva_codigo,
        retencion_iva_porcentaje=data.retencion_iva_porcentaje,
        retencion_renta_codigo=data.retencion_renta_codigo,
        retencion_renta_porcentaje=data.retencion_renta_porcentaje,
        observaciones=data.observaciones,
    )
    db.add(supplier)
    await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="supplier",
        entity_id=supplier.id,
        description=f"Proveedor creado: {data.razon_social} ({data.identificacion})",
        ip_address=request.client.host if request.client else None,
    )

    logger.info(
        f"Proveedor creado: identificación={data.identificacion}, "
        f"empresa={data.company_id}"
    )

    return SupplierResponse.model_validate(supplier)


@router.get("", response_model=list[SupplierResponse])
async def list_suppliers(
    company_id: str | None = None,
    tipo_identificacion: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar proveedores de las empresas del usuario.

    Opcionalmente filtrado por empresa, tipo de identificación y estado activo.
    """
    company_id = clean_company_id(company_id)
    # Consulta base: proveedores de empresas del usuario
    query = (
        select(Supplier)
        .join(Company, Supplier.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    # Filtro de empresa
    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(Supplier.company_id == company_id)

    # Filtro de tipo de identificación
    if tipo_identificacion:
        query = query.where(Supplier.tipo_identificacion == tipo_identificacion)

    # Filtro de estado activo
    if is_active is not None:
        query = query.where(Supplier.is_active == is_active)

    # Ordenar por razón social y paginar
    query = query.order_by(Supplier.razon_social).offset(skip).limit(limit)

    result = await db.execute(query)
    suppliers = result.scalars().all()

    return [SupplierResponse.model_validate(s) for s in suppliers]


@router.get("/{supplier_id}", response_model=SupplierResponse)
async def get_supplier(
    supplier_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un proveedor específico por su ID"""
    supplier_id = validate_uuid(supplier_id, "supplier_id")
    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id)
    )
    supplier = result.scalars().first()

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proveedor no encontrado.",
        )

    # Verificar que la empresa pertenezca al usuario
    await _get_company_for_user(db, supplier.company_id, current_user.id)

    return SupplierResponse.model_validate(supplier)


@router.put("/{supplier_id}", response_model=SupplierResponse)
async def update_supplier(
    supplier_id: str,
    data: SupplierUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar datos de un proveedor"""
    supplier_id = validate_uuid(supplier_id, "supplier_id")
    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id)
    )
    supplier = result.scalars().first()

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proveedor no encontrado.",
        )

    # Verificar que la empresa pertenezca al usuario
    await _get_company_for_user(db, supplier.company_id, current_user.id)

    # Si se cambia la identificación, verificar que no exista otro con la misma
    if data.identificacion and data.identificacion != supplier.identificacion:
        existing = await db.execute(
            select(Supplier).where(
                Supplier.company_id == supplier.company_id,
                Supplier.identificacion == data.identificacion,
                Supplier.id != supplier_id,
                Supplier.is_active == True,
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un proveedor con la identificación '{data.identificacion}' en esta empresa.",
            )

    # Actualizar campos proporcionados
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(supplier, field, value)

    await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="supplier",
        entity_id=supplier.id,
        description=f"Proveedor actualizado: {supplier.razon_social}",
        ip_address=request.client.host if request.client else None,
    )

    logger.info(f"Proveedor actualizado: identificación={supplier.identificacion}")

    return SupplierResponse.model_validate(supplier)


@router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Desactivar un proveedor (eliminación lógica).

    Los proveedores usados en órdenes de compra o cuentas por pagar
    no se eliminan físicamente para mantener la integridad referencial.
    """
    supplier_id = validate_uuid(supplier_id, "supplier_id")
    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id)
    )
    supplier = result.scalars().first()

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proveedor no encontrado.",
        )

    # Verificar que la empresa pertenezca al usuario
    await _get_company_for_user(db, supplier.company_id, current_user.id)

    # Eliminación lógica
    supplier.is_active = False
    await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="supplier",
        entity_id=supplier.id,
        description=f"Proveedor desactivado: {supplier.razon_social}",
        ip_address=request.client.host if request.client else None,
    )

    logger.info(f"Proveedor desactivado: identificación={supplier.identificacion}")

    return {"message": "Proveedor desactivado exitosamente."}

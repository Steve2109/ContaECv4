"""
ContaEC - Endpoints de Multi-Almacén y Logística
CRUD de almacenes, ubicaciones, transferencias y stock por almacén
"""
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_action
from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.company import Company
from app.models.kardex import Kardex, KardexTipoMovimiento
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import (
    TransferEstado,
    Warehouse,
    WarehouseLocation,
    WarehouseTransfer,
    WarehouseTransferDetalle,
)
from app.schemas.warehouse import (
    KardexDetalladoResponse,
    WarehouseCreate,
    WarehouseLocationCreate,
    WarehouseLocationResponse,
    WarehouseLocationUpdate,
    WarehouseResponse,
    WarehouseStockResponse,
    WarehouseTransferCreate,
    WarehouseTransferResponse,
    WarehouseUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/warehouses", tags=["Multi-Almacén y Logística"])


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


async def _get_next_number(db: AsyncSession, company_id: str, prefix: str, table) -> str:
    """Genera el siguiente número secuencial para una tabla dada"""
    result = await db.execute(
        select(func.count(table.id)).where(table.company_id == company_id)
    )
    count = result.scalar() or 0
    return f"{prefix}-{str(count + 1).zfill(6)}"


def _build_codigo_ubicacion(
    zona: str,
    pasillo: str | None,
    rack: str | None,
    estante: str | None,
    nivel: str | None,
) -> str:
    """Construye el código corto de ubicación a partir de sus componentes."""
    parts = [zona]
    if pasillo:
        parts.append(f"P{pasillo}")
    if rack:
        parts.append(f"R{rack}")
    if estante:
        parts.append(f"E{estante}")
    if nivel:
        parts.append(f"N{nivel}")
    return "-".join(parts)


def _build_ubicacion_completa(
    zona: str,
    pasillo: str | None,
    rack: str | None,
    estante: str | None,
    nivel: str | None,
) -> str:
    """Construye la descripción completa de la ubicación."""
    parts = [f"Zona{zona}"]
    if pasillo:
        parts.append(f"Pasillo{pasillo}")
    if rack:
        parts.append(f"Rack{rack}")
    if estante:
        parts.append(f"Estante{estante}")
    if nivel:
        parts.append(f"Nivel{nivel}")
    return "-".join(parts)


# ==========================================
# Almacenes - CRUD
# ==========================================

@router.get("", response_model=list[WarehouseResponse])
async def list_warehouses(
    company_id: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar almacenes de la empresa"""
    company_id = clean_company_id(company_id)
    try:
        query = (
            select(Warehouse)
            .join(Company, Warehouse.company_id == Company.id)
            .where(Company.user_id == current_user.id)
        )

        if company_id:
            await _get_company_for_user(db, company_id, current_user.id)
            query = query.where(Warehouse.company_id == company_id)
        if is_active is not None:
            query = query.where(Warehouse.is_active == is_active)

        query = query.order_by(Warehouse.created_at.desc()).offset(skip).limit(limit)

        result = await db.execute(query)
        warehouses = result.scalars().all()
        return [WarehouseResponse.model_validate(w) for w in warehouses]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing warehouses: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar almacenes: {str(e)}",
        )


@router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    data: WarehouseCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un nuevo almacén"""
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, current_user.id)

    # Verificar que el código sea único por empresa
    existing = await db.execute(
        select(Warehouse).where(
            Warehouse.company_id == data.company_id,
            Warehouse.codigo == data.codigo,
            Warehouse.is_active == True,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un almacén con el código '{data.codigo}' en esta empresa.",
        )

    # Si se marca como principal, desmarcar el anterior
    if data.is_principal:
        result = await db.execute(
            select(Warehouse).where(
                Warehouse.company_id == data.company_id,
                Warehouse.is_principal == True,
                Warehouse.is_active == True,
            )
        )
        current_principal = result.scalars().first()
        if current_principal:
            current_principal.is_principal = False

    warehouse = Warehouse(
        company_id=data.company_id,
        nombre=data.nombre,
        codigo=data.codigo,
        direccion=data.direccion,
        ciudad=data.ciudad,
        responsable=data.responsable,
        telefono=data.telefono,
        is_principal=data.is_principal,
    )
    db.add(warehouse)
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="CREATE", entity_type="warehouse", entity_id=warehouse.id,
        description=f"Almacén creado: {data.nombre} ({data.codigo})",
        ip_address=request.client.host if request.client else None,
    )

    return WarehouseResponse.model_validate(warehouse)


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(
    warehouse_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un almacén específico con sus ubicaciones"""
    warehouse_id = validate_uuid(warehouse_id, "warehouse_id")
    result = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id)
    )
    warehouse = result.scalars().first()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado.")
    await _get_company_for_user(db, warehouse.company_id, current_user.id)
    return WarehouseResponse.model_validate(warehouse)


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: str,
    data: WarehouseUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar un almacén"""
    warehouse_id = validate_uuid(warehouse_id, "warehouse_id")
    result = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id)
    )
    warehouse = result.scalars().first()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado.")
    await _get_company_for_user(db, warehouse.company_id, current_user.id)

    # Si se actualiza el código, verificar unicidad
    if data.codigo and data.codigo != warehouse.codigo:
        existing = await db.execute(
            select(Warehouse).where(
                Warehouse.company_id == warehouse.company_id,
                Warehouse.codigo == data.codigo,
                Warehouse.is_active == True,
                Warehouse.id != warehouse_id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un almacén con el código '{data.codigo}'.",
            )

    # Si se marca como principal, desmarcar el anterior
    if data.is_principal and not warehouse.is_principal:
        result = await db.execute(
            select(Warehouse).where(
                Warehouse.company_id == warehouse.company_id,
                Warehouse.is_principal == True,
                Warehouse.is_active == True,
                Warehouse.id != warehouse_id,
            )
        )
        current_principal = result.scalars().first()
        if current_principal:
            current_principal.is_principal = False

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(warehouse, field, value)

    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="warehouse", entity_id=warehouse.id,
        description=f"Almacén actualizado: {warehouse.nombre} ({warehouse.codigo})",
        ip_address=request.client.host if request.client else None,
    )

    return WarehouseResponse.model_validate(warehouse)


@router.delete("/{warehouse_id}")
async def deactivate_warehouse(
    warehouse_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Desactivar un almacén (eliminación lógica)"""
    warehouse_id = validate_uuid(warehouse_id, "warehouse_id")
    result = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id)
    )
    warehouse = result.scalars().first()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado.")
    await _get_company_for_user(db, warehouse.company_id, current_user.id)

    # Verificar que no sea el almacén principal
    if warehouse.is_principal:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede desactivar el almacén principal. Asigne otro almacén como principal primero.",
        )

    warehouse.is_active = False
    warehouse.is_principal = False
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="DELETE", entity_type="warehouse", entity_id=warehouse.id,
        description=f"Almacén desactivado: {warehouse.nombre} ({warehouse.codigo})",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Almacén desactivado exitosamente."}


# ==========================================
# Ubicaciones de Almacén
# ==========================================

@router.get("/{warehouse_id}/locations", response_model=list[WarehouseLocationResponse])
async def list_warehouse_locations(
    warehouse_id: str,
    is_active: bool | None = True,
    product_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar ubicaciones de un almacén"""
    product_id = clean_uuid_param(product_id, "product_id")
    warehouse_id = validate_uuid(warehouse_id, "warehouse_id")
    result = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id)
    )
    warehouse = result.scalars().first()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado.")
    await _get_company_for_user(db, warehouse.company_id, current_user.id)

    query = select(WarehouseLocation).where(WarehouseLocation.warehouse_id == warehouse_id)
    if is_active is not None:
        query = query.where(WarehouseLocation.is_active == is_active)
    if product_id:
        query = query.where(WarehouseLocation.producto_id == product_id)

    query = query.order_by(
        WarehouseLocation.zona,
        WarehouseLocation.pasillo.nulls_first(),
        WarehouseLocation.rack.nulls_first(),
        WarehouseLocation.estante.nulls_first(),
    )
    result = await db.execute(query)
    locations = result.scalars().all()
    return [WarehouseLocationResponse.model_validate(loc) for loc in locations]


@router.post("/{warehouse_id}/locations", response_model=WarehouseLocationResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse_location(
    warehouse_id: str,
    data: WarehouseLocationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una ubicación dentro de un almacén"""
    data.producto_id = clean_uuid_param(data.producto_id, "producto_id")
    warehouse_id = validate_uuid(warehouse_id, "warehouse_id")
    result = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id)
    )
    warehouse = result.scalars().first()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado.")
    await _get_company_for_user(db, warehouse.company_id, current_user.id)

    # Generar códigos de ubicación
    codigo_ubicacion = _build_codigo_ubicacion(
        data.zona, data.pasillo, data.rack, data.estante, data.nivel
    )
    ubicacion_completa = _build_ubicacion_completa(
        data.zona, data.pasillo, data.rack, data.estante, data.nivel
    )

    # Verificar que no exista una ubicación con el mismo código en el almacén
    existing = await db.execute(
        select(WarehouseLocation).where(
            WarehouseLocation.warehouse_id == warehouse_id,
            WarehouseLocation.codigo_ubicacion == codigo_ubicacion,
            WarehouseLocation.is_active == True,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una ubicación con el código '{codigo_ubicacion}' en este almacén.",
        )

    location = WarehouseLocation(
        warehouse_id=warehouse_id,
        producto_id=data.producto_id,
        zona=data.zona,
        pasillo=data.pasillo,
        rack=data.rack,
        estante=data.estante,
        nivel=data.nivel,
        codigo_ubicacion=codigo_ubicacion,
        ubicacion_completa=ubicacion_completa,
        capacidad_maxima=data.capacidad_maxima,
        capacidad_actual=data.capacidad_actual,
    )
    db.add(location)
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="CREATE", entity_type="warehouse_location", entity_id=location.id,
        description=f"Ubicación creada: {codigo_ubicacion} en almacén {warehouse.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return WarehouseLocationResponse.model_validate(location)


@router.put("/locations/{location_id}", response_model=WarehouseLocationResponse)
async def update_warehouse_location(
    location_id: str,
    data: WarehouseLocationUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una ubicación de almacén"""
    location_id = validate_uuid(location_id, "location_id")
    result = await db.execute(
        select(WarehouseLocation).where(WarehouseLocation.id == location_id)
    )
    location = result.scalars().first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada.")

    # Verificar acceso al almacén
    wh_result = await db.execute(
        select(Warehouse).where(Warehouse.id == location.warehouse_id)
    )
    warehouse = wh_result.scalars().first()
    if warehouse:
        await _get_company_for_user(db, warehouse.company_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    # Validar capacidad si se actualiza
    new_max = update_data.get("capacidad_maxima", location.capacidad_maxima)
    new_actual = update_data.get("capacidad_actual", location.capacidad_actual)
    if new_max is not None and new_actual > new_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La ocupación actual ({new_actual}) no puede exceder "
                f"la capacidad máxima ({new_max})."
            ),
        )

    # Si se actualizan componentes, regenerar códigos
    if any(k in update_data for k in ("zona", "pasillo", "rack", "estante", "nivel")):
        new_zona = update_data.get("zona", location.zona)
        new_pasillo = update_data.get("pasillo", location.pasillo)
        new_rack = update_data.get("rack", location.rack)
        new_estante = update_data.get("estante", location.estante)
        new_nivel = update_data.get("nivel", location.nivel)

        new_codigo = _build_codigo_ubicacion(
            new_zona, new_pasillo, new_rack, new_estante, new_nivel
        )
        new_completa = _build_ubicacion_completa(
            new_zona, new_pasillo, new_rack, new_estante, new_nivel
        )

        if new_codigo != location.codigo_ubicacion:
            existing = await db.execute(
                select(WarehouseLocation).where(
                    WarehouseLocation.warehouse_id == location.warehouse_id,
                    WarehouseLocation.codigo_ubicacion == new_codigo,
                    WarehouseLocation.is_active == True,
                    WarehouseLocation.id != location_id,
                )
            )
            if existing.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ya existe una ubicación con el código '{new_codigo}'.",
                )

        update_data["codigo_ubicacion"] = new_codigo
        update_data["ubicacion_completa"] = new_completa

    for field, value in update_data.items():
        setattr(location, field, value)

    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="warehouse_location", entity_id=location.id,
        description=f"Ubicación actualizada: {location.codigo_ubicacion}",
        ip_address=request.client.host if request.client else None,
    )

    return WarehouseLocationResponse.model_validate(location)


@router.delete("/locations/{location_id}")
async def deactivate_warehouse_location(
    location_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Desactivar una ubicación de almacén"""
    location_id = validate_uuid(location_id, "location_id")
    result = await db.execute(
        select(WarehouseLocation).where(WarehouseLocation.id == location_id)
    )
    location = result.scalars().first()
    if not location:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ubicación no encontrada.")

    # Verificar acceso al almacén
    wh_result = await db.execute(
        select(Warehouse).where(Warehouse.id == location.warehouse_id)
    )
    warehouse = wh_result.scalars().first()
    if warehouse:
        await _get_company_for_user(db, warehouse.company_id, current_user.id)

    location.is_active = False
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="DELETE", entity_type="warehouse_location", entity_id=location.id,
        description=f"Ubicación desactivada: {location.codigo_ubicacion}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Ubicación desactivada exitosamente."}


# ==========================================
# Stock por Almacén
# ==========================================

@router.get("/{warehouse_id}/stock", response_model=list[WarehouseStockResponse])
async def get_warehouse_stock(
    warehouse_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener resumen de stock de un almacén"""
    warehouse_id = validate_uuid(warehouse_id, "warehouse_id")
    result = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id)
    )
    warehouse = result.scalars().first()
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Almacén no encontrado.")
    await _get_company_for_user(db, warehouse.company_id, current_user.id)

    # Obtener último kardex por producto para este almacén
    # Subconsulta: último movimiento por producto en este almacén
    subquery = (
        select(
            Kardex.product_id,
            func.max(Kardex.created_at).label("max_created")
        )
        .where(
            Kardex.company_id == warehouse.company_id,
            Kardex.warehouse_id == warehouse_id,
            Kardex.is_active == True,
        )
        .group_by(Kardex.product_id)
    )

    # Query principal: obtener los movimientos más recientes por producto
    result = await db.execute(
        select(
            Kardex.product_id,
            Product.codigo_principal,
            Product.descripcion,
            Kardex.saldo_cantidad,
            Kardex.saldo_valor,
        )
        .join(Product, Kardex.product_id == Product.id)
        .where(
            Kardex.company_id == warehouse.company_id,
            Kardex.warehouse_id == warehouse_id,
            Kardex.is_active == True,
            Kardex.created_at.in_(
                select(func.max(Kardex.created_at)).where(
                    Kardex.company_id == warehouse.company_id,
                    Kardex.warehouse_id == warehouse_id,
                    Kardex.is_active == True,
                ).group_by(Kardex.product_id)
            ),
        )
        .group_by(Kardex.product_id, Product.codigo_principal, Product.descripcion, Kardex.saldo_cantidad, Kardex.saldo_valor)
    )

    stocks = []
    for row in result:
        costo_promedio = Decimal("0")
        if row.saldo_cantidad and row.saldo_cantidad > 0 and row.saldo_valor:
            costo_promedio = row.saldo_valor / row.saldo_cantidad
        stocks.append(WarehouseStockResponse(
            product_id=row.product_id,
            producto_codigo=row.codigo_principal,
            producto_descripcion=row.descripcion,
            saldo_cantidad=row.saldo_cantidad or Decimal("0"),
            saldo_valor=row.saldo_valor or Decimal("0"),
            costo_promedio=costo_promedio,
        ))

    return stocks


# ==========================================
# Transferencias entre Almacenes
# ==========================================

@router.post("/transfers", response_model=WarehouseTransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    data: WarehouseTransferCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva transferencia entre almacenes"""
    data.warehouse_origen_id = clean_uuid_param(data.warehouse_origen_id, "warehouse_origen_id")
    data.warehouse_destino_id = clean_uuid_param(data.warehouse_destino_id, "warehouse_destino_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, current_user.id)

    # Verificar almacén de origen
    origen_result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == data.warehouse_origen_id,
            Warehouse.company_id == data.company_id,
            Warehouse.is_active == True,
        )
    )
    if not origen_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacén de origen no encontrado o no pertenece a la empresa.",
        )

    # Verificar almacén de destino
    destino_result = await db.execute(
        select(Warehouse).where(
            Warehouse.id == data.warehouse_destino_id,
            Warehouse.company_id == data.company_id,
            Warehouse.is_active == True,
        )
    )
    if not destino_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacén de destino no encontrado o no pertenece a la empresa.",
        )

    # Verificar que origen != destino
    if data.warehouse_origen_id == data.warehouse_destino_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El almacén de origen y destino deben ser diferentes.",
        )

    # Generar número secuencial
    numero = await _get_next_number(db, data.company_id, "TR", WarehouseTransfer)

    # Crear detalles
    detalles = []
    for det in data.detalles:
        costo_total = det.cantidad * det.costo_unitario
        detalles.append(WarehouseTransferDetalle(
            product_id=det.product_id,
            cantidad=det.cantidad,
            costo_unitario=det.costo_unitario,
            costo_total=costo_total,
            ubicacion_origen_id=det.ubicacion_origen_id,
            ubicacion_destino_id=det.ubicacion_destino_id,
        ))

    transfer = WarehouseTransfer(
        company_id=data.company_id,
        numero=numero,
        warehouse_origen_id=data.warehouse_origen_id,
        warehouse_destino_id=data.warehouse_destino_id,
        estado=TransferEstado.PENDIENTE.value,
        motivo=data.motivo,
        observaciones=data.observaciones,
        user_id=current_user.id,
        detalles=detalles,
    )
    db.add(transfer)
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="CREATE", entity_type="warehouse_transfer", entity_id=transfer.id,
        description=f"Transferencia creada: {numero}",
        ip_address=request.client.host if request.client else None,
    )

    return WarehouseTransferResponse.model_validate(transfer)


@router.get("/transfers", response_model=list[WarehouseTransferResponse])
async def list_transfers(
    company_id: str | None = None,
    estado: str | None = None,
    warehouse_id: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar transferencias entre almacenes"""
    warehouse_id = clean_uuid_param(warehouse_id, "warehouse_id")
    company_id = clean_company_id(company_id)
    query = (
        select(WarehouseTransfer)
        .join(Company, WarehouseTransfer.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(WarehouseTransfer.company_id == company_id)
    if estado:
        query = query.where(WarehouseTransfer.estado == estado)
    if warehouse_id:
        query = query.where(
            (WarehouseTransfer.warehouse_origen_id == warehouse_id) |
            (WarehouseTransfer.warehouse_destino_id == warehouse_id)
        )

    query = query.order_by(WarehouseTransfer.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    transfers = result.scalars().all()
    return [WarehouseTransferResponse.model_validate(t) for t in transfers]


@router.get("/transfers/{transfer_id}", response_model=WarehouseTransferResponse)
async def get_transfer(
    transfer_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una transferencia específica con sus detalles"""
    transfer_id = validate_uuid(transfer_id, "transfer_id")
    result = await db.execute(
        select(WarehouseTransfer).where(WarehouseTransfer.id == transfer_id)
    )
    transfer = result.scalars().first()
    if not transfer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transferencia no encontrada.")
    await _get_company_for_user(db, transfer.company_id, current_user.id)
    return WarehouseTransferResponse.model_validate(transfer)


@router.put("/transfers/{transfer_id}/enviar", response_model=WarehouseTransferResponse)
async def send_transfer(
    transfer_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marcar transferencia como enviada (pendiente → en_transito)"""
    transfer_id = validate_uuid(transfer_id, "transfer_id")
    result = await db.execute(
        select(WarehouseTransfer).where(WarehouseTransfer.id == transfer_id)
    )
    transfer = result.scalars().first()
    if not transfer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transferencia no encontrada.")
    await _get_company_for_user(db, transfer.company_id, current_user.id)

    if transfer.estado != TransferEstado.PENDIENTE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden enviar transferencias en estado 'pendiente'. Estado actual: '{transfer.estado}'.",
        )

    transfer.estado = TransferEstado.EN_TRANSITO.value
    transfer.fecha_envio = datetime.now(timezone.utc)
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="warehouse_transfer", entity_id=transfer.id,
        description=f"Transferencia enviada: {transfer.numero}",
        ip_address=request.client.host if request.client else None,
    )

    return WarehouseTransferResponse.model_validate(transfer)


@router.put("/transfers/{transfer_id}/recibir", response_model=WarehouseTransferResponse)
async def receive_transfer(
    transfer_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Marcar transferencia como recibida (en_transito → recibida).
    Actualiza kardex para ambos almacenes: salida del origen y entrada al destino.
    """
    transfer_id = validate_uuid(transfer_id, "transfer_id")
    result = await db.execute(
        select(WarehouseTransfer).where(WarehouseTransfer.id == transfer_id)
    )
    transfer = result.scalars().first()
    if not transfer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transferencia no encontrada.")
    await _get_company_for_user(db, transfer.company_id, current_user.id)

    if transfer.estado != TransferEstado.EN_TRANSITO.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden recibir transferencias en estado 'en_transito'. Estado actual: '{transfer.estado}'.",
        )

    # Actualizar estado
    transfer.estado = TransferEstado.RECIBIDA.value
    transfer.fecha_recepcion = datetime.now(timezone.utc)

    # Registrar movimientos en kardex para cada detalle
    for det in transfer.detalles:
        # === SALIDA del almacén de origen ===
        # Obtener saldo actual en el almacén de origen
        last_saldo_origen = await db.execute(
            select(Kardex)
            .where(
                Kardex.product_id == det.product_id,
                Kardex.company_id == transfer.company_id,
                Kardex.warehouse_id == transfer.warehouse_origen_id,
                Kardex.is_active == True,
            )
            .order_by(Kardex.fecha_movimiento.desc(), Kardex.created_at.desc())
            .limit(1)
        )
        last_mov_origen = last_saldo_origen.scalars().first()
        saldo_cantidad_origen = last_mov_origen.saldo_cantidad if last_mov_origen else Decimal("0")
        saldo_valor_origen = last_mov_origen.saldo_valor if last_mov_origen else Decimal("0")

        # Calcular nuevo saldo (salida)
        costo_promedio = Decimal("0")
        if saldo_cantidad_origen > 0:
            costo_promedio = saldo_valor_origen / saldo_cantidad_origen

        nuevo_saldo_cantidad_origen = saldo_cantidad_origen - det.cantidad
        nuevo_saldo_valor_origen = saldo_valor_origen - (det.cantidad * costo_promedio)

        if nuevo_saldo_cantidad_origen < 0:
            nuevo_saldo_cantidad_origen = Decimal("0")
            nuevo_saldo_valor_origen = Decimal("0")

        kardex_salida = Kardex(
            company_id=transfer.company_id,
            product_id=det.product_id,
            warehouse_id=transfer.warehouse_origen_id,
            tipo_movimiento=KardexTipoMovimiento.SALIDA.value,
            cantidad=det.cantidad,
            costo_unitario=det.costo_unitario,
            costo_total=det.costo_total,
            saldo_cantidad=nuevo_saldo_cantidad_origen,
            saldo_valor=nuevo_saldo_valor_origen,
            referencia_tipo="transferencia",
            referencia_id=transfer.id,
            referencia_secuencial=transfer.numero,
            detalle=f"Salida por transferencia {transfer.numero} a almacén destino",
            fecha_movimiento=datetime.now(timezone.utc),
            user_id=current_user.id,
        )
        db.add(kardex_salida)

        # === ENTRADA al almacén de destino ===
        last_saldo_destino = await db.execute(
            select(Kardex)
            .where(
                Kardex.product_id == det.product_id,
                Kardex.company_id == transfer.company_id,
                Kardex.warehouse_id == transfer.warehouse_destino_id,
                Kardex.is_active == True,
            )
            .order_by(Kardex.fecha_movimiento.desc(), Kardex.created_at.desc())
            .limit(1)
        )
        last_mov_destino = last_saldo_destino.scalars().first()
        saldo_cantidad_destino = last_mov_destino.saldo_cantidad if last_mov_destino else Decimal("0")
        saldo_valor_destino = last_mov_destino.saldo_valor if last_mov_destino else Decimal("0")

        nuevo_saldo_cantidad_destino = saldo_cantidad_destino + det.cantidad
        nuevo_saldo_valor_destino = saldo_valor_destino + det.costo_total

        kardex_entrada = Kardex(
            company_id=transfer.company_id,
            product_id=det.product_id,
            warehouse_id=transfer.warehouse_destino_id,
            tipo_movimiento=KardexTipoMovimiento.ENTRADA.value,
            cantidad=det.cantidad,
            costo_unitario=det.costo_unitario,
            costo_total=det.costo_total,
            saldo_cantidad=nuevo_saldo_cantidad_destino,
            saldo_valor=nuevo_saldo_valor_destino,
            referencia_tipo="transferencia",
            referencia_id=transfer.id,
            referencia_secuencial=transfer.numero,
            detalle=f"Entrada por transferencia {transfer.numero} desde almacén origen",
            fecha_movimiento=datetime.now(timezone.utc),
            user_id=current_user.id,
        )
        db.add(kardex_entrada)

        # Actualizar cantidades en ubicaciones si están definidas
        if det.ubicacion_origen_id:
            loc_origen = await db.execute(
                select(WarehouseLocation).where(WarehouseLocation.id == det.ubicacion_origen_id)
            )
            loc_origen_obj = loc_origen.scalars().first()
            if loc_origen_obj:
                loc_origen_obj.capacidad_actual = max(
                    0, loc_origen_obj.capacidad_actual - int(det.cantidad)
                )

        if det.ubicacion_destino_id:
            loc_destino = await db.execute(
                select(WarehouseLocation).where(WarehouseLocation.id == det.ubicacion_destino_id)
            )
            loc_destino_obj = loc_destino.scalars().first()
            if loc_destino_obj:
                loc_destino_obj.capacidad_actual += int(det.cantidad)

    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="warehouse_transfer", entity_id=transfer.id,
        description=f"Transferencia recibida: {transfer.numero}. Kardex actualizado para ambos almacenes.",
        ip_address=request.client.host if request.client else None,
    )

    return WarehouseTransferResponse.model_validate(transfer)


@router.put("/transfers/{transfer_id}/anular", response_model=WarehouseTransferResponse)
async def cancel_transfer(
    transfer_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Anular una transferencia (pendiente → anulada)"""
    transfer_id = validate_uuid(transfer_id, "transfer_id")
    result = await db.execute(
        select(WarehouseTransfer).where(WarehouseTransfer.id == transfer_id)
    )
    transfer = result.scalars().first()
    if not transfer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transferencia no encontrada.")
    await _get_company_for_user(db, transfer.company_id, current_user.id)

    if transfer.estado != TransferEstado.PENDIENTE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden anular transferencias en estado 'pendiente'. Estado actual: '{transfer.estado}'.",
        )

    transfer.estado = TransferEstado.ANULADA.value
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="warehouse_transfer", entity_id=transfer.id,
        description=f"Transferencia anulada: {transfer.numero}",
        ip_address=request.client.host if request.client else None,
    )

    return WarehouseTransferResponse.model_validate(transfer)


# ==========================================
# Kardex Detallado con información de almacén
# ==========================================

@router.get("/kardex/detallado", response_model=list[KardexDetalladoResponse])
async def get_kardex_detallado(
    company_id: str = Query(..., description="ID de la empresa"),
    product_id: str | None = None,
    warehouse_id: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    tipo_movimiento: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=2000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener kardex detallado con información de almacén"""
    product_id = clean_uuid_param(product_id, "product_id")
    warehouse_id = clean_uuid_param(warehouse_id, "warehouse_id")
    company_id = validate_uuid(company_id, "company_id")
    await _get_company_for_user(db, company_id, current_user.id)

    query = (
        select(Kardex)
        .where(
            Kardex.company_id == company_id,
            Kardex.is_active == True,
        )
    )

    if product_id:
        query = query.where(Kardex.product_id == product_id)
    if warehouse_id:
        query = query.where(Kardex.warehouse_id == warehouse_id)
    if fecha_desde:
        query = query.where(Kardex.fecha_movimiento >= fecha_desde)
    if fecha_hasta:
        query = query.where(Kardex.fecha_movimiento <= fecha_hasta)
    if tipo_movimiento:
        query = query.where(Kardex.tipo_movimiento == tipo_movimiento)

    query = query.order_by(Kardex.fecha_movimiento.desc(), Kardex.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    movements = result.scalars().all()

    # Obtener nombres de almacenes
    warehouse_ids = set()
    for m in movements:
        if m.warehouse_id:
            warehouse_ids.add(m.warehouse_id)

    warehouse_names = {}
    if warehouse_ids:
        wh_result = await db.execute(
            select(Warehouse.id, Warehouse.nombre).where(Warehouse.id.in_(warehouse_ids))
        )
        for row in wh_result:
            warehouse_names[row[0]] = row[1]

    responses = []
    for m in movements:
        responses.append(KardexDetalladoResponse(
            id=m.id,
            company_id=m.company_id,
            product_id=m.product_id,
            warehouse_id=m.warehouse_id,
            warehouse_nombre=warehouse_names.get(m.warehouse_id) if m.warehouse_id else None,
            tipo_movimiento=m.tipo_movimiento,
            cantidad=m.cantidad,
            costo_unitario=m.costo_unitario,
            costo_total=m.costo_total,
            saldo_cantidad=m.saldo_cantidad,
            saldo_valor=m.saldo_valor,
            referencia_tipo=m.referencia_tipo,
            referencia_id=m.referencia_id,
            referencia_secuencial=m.referencia_secuencial,
            detalle=m.detalle,
            fecha_movimiento=m.fecha_movimiento,
            user_id=m.user_id,
            is_active=m.is_active,
            created_at=m.created_at,
        ))

    return responses

"""
ContaEC - Endpoints de Ubicaciones Fisicas de Almacen
CRUD para ubicaciones con tracking de rack/shelf/bin, capacidad y mapa visual
"""
import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_action
from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.company import Company
from app.models.kardex import Kardex
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse, WarehouseLocation
from app.schemas.warehouse import (
    WarehouseLocationCreate,
    WarehouseLocationMapResponse,
    WarehouseLocationResponse,
    WarehouseLocationStockResponse,
    WarehouseLocationUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ubicaciones", tags=["Ubicaciones Fisicas"])


# ==========================================
# Funciones auxiliares
# ==========================================

async def _get_warehouse_for_user(
    db: AsyncSession,
    warehouse_id: str,
    user_id: str,
) -> Warehouse:
    """Obtiene un almacen verificando que pertenezca a la empresa del usuario actual."""
    result = await db.execute(
        select(Warehouse)
        .join(Company, Warehouse.company_id == Company.id)
        .where(
            Warehouse.id == warehouse_id,
            Company.user_id == user_id,
            Company.is_active == True,
            Warehouse.is_active == True,
        )
    )
    warehouse = result.scalars().first()
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Almacen no encontrado o no pertenece al usuario actual.",
        )
    return warehouse


async def _get_location_for_user(
    db: AsyncSession,
    location_id: str,
    user_id: str,
) -> WarehouseLocation:
    """Obtiene una ubicacion verificando acceso via almacen -> empresa -> usuario."""
    result = await db.execute(
        select(WarehouseLocation)
        .join(Warehouse, WarehouseLocation.warehouse_id == Warehouse.id)
        .join(Company, Warehouse.company_id == Company.id)
        .where(
            WarehouseLocation.id == location_id,
            Company.user_id == user_id,
            Company.is_active == True,
        )
    )
    location = result.scalars().first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ubicacion no encontrada o no pertenece al usuario actual.",
        )
    return location


def _build_codigo_ubicacion(
    zona: str,
    pasillo: str | None,
    rack: str | None,
    estante: str | None,
    nivel: str | None,
) -> str:
    """Construye el codigo corto de ubicacion a partir de sus componentes."""
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
    """Construye la descripcion completa de la ubicacion."""
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
# Ubicaciones - CRUD Principal
# ==========================================

@router.get("", response_model=list[WarehouseLocationResponse])
async def list_ubicaciones(
    warehouse_id: str | None = Query(
        None, description="Filtrar por ID de almacen"
    ),
    zona: str | None = Query(
        None, description="Filtrar por zona (ej: A, B, Refrigerados)"
    ),
    disponible: bool | None = Query(
        None,
        description="True=ubicaciones sin producto asignado, False=con producto asignado",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar ubicaciones fisicas con filtros opcionales.

    Filtros:
    - **warehouse_id**: Ubicaciones de un almacen especifico
    - **zona**: Ubicaciones en una zona especifica
    - **disponible**: True para ubicaciones sin producto, False con producto
    """
    warehouse_id = clean_uuid_param(warehouse_id, "warehouse_id")
    query = (
        select(WarehouseLocation)
        .join(Warehouse, WarehouseLocation.warehouse_id == Warehouse.id)
        .join(Company, Warehouse.company_id == Company.id)
        .where(
            Company.user_id == current_user.id,
            Company.is_active == True,
            Warehouse.is_active == True,
        )
    )

    if warehouse_id:
        await _get_warehouse_for_user(db, warehouse_id, current_user.id)
        query = query.where(WarehouseLocation.warehouse_id == warehouse_id)
    if zona:
        query = query.where(WarehouseLocation.zona == zona)
    if disponible is True:
        query = query.where(WarehouseLocation.producto_id.is_(None))
    elif disponible is False:
        query = query.where(WarehouseLocation.producto_id.isnot(None))

    query = query.order_by(
        Warehouse.nombre,
        WarehouseLocation.zona,
        WarehouseLocation.pasillo.nulls_first(),
        WarehouseLocation.rack.nulls_first(),
        WarehouseLocation.estante.nulls_first(),
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    locations = result.scalars().all()
    return [WarehouseLocationResponse.model_validate(loc) for loc in locations]


@router.get(
    "/{ubicacion_id}",
    response_model=WarehouseLocationResponse,
)
async def get_ubicacion(
    ubicacion_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener detalle de una ubicacion fisica."""
    ubicacion_id = validate_uuid(ubicacion_id, "ubicacion_id")
    location = await _get_location_for_user(db, ubicacion_id, current_user.id)
    return WarehouseLocationResponse.model_validate(location)


@router.post(
    "",
    response_model=WarehouseLocationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ubicacion(
    warehouse_id: str,
    data: WarehouseLocationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva ubicacion fisica en un almacen.

    Valida:
    - Que el almacen exista y pertenezca al usuario
    - Que no exista otra ubicacion con el mismo codigo en el almacen
    - Que capacidad_actual no exceda capacidad_maxima
    """
    data.producto_id = clean_uuid_param(data.producto_id, "producto_id")
    warehouse_id = validate_uuid(warehouse_id, "warehouse_id")
    warehouse = await _get_warehouse_for_user(db, warehouse_id, current_user.id)

    # Validar capacidad
    if data.capacidad_maxima is not None and data.capacidad_actual > data.capacidad_maxima:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La ocupacion actual ({data.capacidad_actual}) no puede exceder "
                f"la capacidad maxima ({data.capacidad_maxima})."
            ),
        )

    # Construir codigos
    codigo_ubicacion = _build_codigo_ubicacion(
        data.zona, data.pasillo, data.rack, data.estante, data.nivel
    )
    ubicacion_completa = _build_ubicacion_completa(
        data.zona, data.pasillo, data.rack, data.estante, data.nivel
    )

    # Verificar unicidad del codigo en el almacen
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
            detail=f"Ya existe una ubicacion con el codigo '{codigo_ubicacion}' en este almacen.",
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
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="warehouse_location",
        entity_id=location.id,
        description=f"Ubicacion fisica creada: {ubicacion_completa} en almacen {warehouse.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return WarehouseLocationResponse.model_validate(location)


@router.put(
    "/{ubicacion_id}",
    response_model=WarehouseLocationResponse,
)
async def update_ubicacion(
    ubicacion_id: str,
    data: WarehouseLocationUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una ubicacion fisica."""
    ubicacion_id = validate_uuid(ubicacion_id, "ubicacion_id")
    location = await _get_location_for_user(db, ubicacion_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    # Validar capacidad si se actualiza
    new_max = update_data.get("capacidad_maxima", location.capacidad_maxima)
    new_actual = update_data.get("capacidad_actual", location.capacidad_actual)
    if new_max is not None and new_actual > new_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"La ocupacion actual ({new_actual}) no puede exceder "
                f"la capacidad maxima ({new_max})."
            ),
        )

    # Si se actualizan componentes, regenerar codigos
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
                    WarehouseLocation.id != ubicacion_id,
                )
            )
            if existing.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ya existe una ubicacion con el codigo '{new_codigo}'.",
                )

        update_data["codigo_ubicacion"] = new_codigo
        update_data["ubicacion_completa"] = new_completa

    for field, value in update_data.items():
        setattr(location, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="warehouse_location",
        entity_id=location.id,
        description=f"Ubicacion fisica actualizada: {location.ubicacion_completa}",
        ip_address=request.client.host if request.client else None,
    )

    return WarehouseLocationResponse.model_validate(location)


@router.delete("/{ubicacion_id}")
async def deactivate_ubicacion(
    ubicacion_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Desactivar una ubicacion fisica (soft delete).

    Solo se permite si la ubicacion esta vacia (capacidad_actual == 0)
    y no tiene producto asignado.
    """
    ubicacion_id = validate_uuid(ubicacion_id, "ubicacion_id")
    location = await _get_location_for_user(db, ubicacion_id, current_user.id)

    # Solo desactivar si esta vacia
    if location.capacidad_actual > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No se puede desactivar la ubicacion '{location.codigo_ubicacion}' "
                f"porque tiene {location.capacidad_actual} unidades ocupando espacio."
            ),
        )

    if location.producto_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No se puede desactivar la ubicacion '{location.codigo_ubicacion}' "
                f"porque tiene un producto asignado."
            ),
        )

    location.is_active = False
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="warehouse_location",
        entity_id=location.id,
        description=f"Ubicacion fisica desactivada: {location.codigo_ubicacion}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": f"Ubicacion '{location.codigo_ubicacion}' desactivada exitosamente."}


# ==========================================
# Stock en Ubicacion
# ==========================================

@router.get(
    "/{ubicacion_id}/stock",
    response_model=list[WarehouseLocationStockResponse],
)
async def get_ubicacion_stock(
    ubicacion_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener el stock actual en una ubicacion fisica.

    Retorna los productos asignados a esta ubicacion con sus cantidades
    obtenidas del ultimo registro kardex.
    """
    ubicacion_id = validate_uuid(ubicacion_id, "ubicacion_id")
    location = await _get_location_for_user(db, ubicacion_id, current_user.id)

    if location.producto_id is None:
        return []

    # Obtener el ultimo kardex para este producto en el almacen de la ubicacion
    result = await db.execute(
        select(
            Kardex.product_id,
            Product.codigo_principal,
            Product.descripcion,
            Kardex.saldo_cantidad,
        )
        .join(Product, Kardex.product_id == Product.id)
        .where(
            Kardex.product_id == location.producto_id,
            Kardex.warehouse_id == location.warehouse_id,
            Kardex.is_active == True,
            Kardex.created_at == select(func.max(Kardex.created_at)).where(
                Kardex.product_id == location.producto_id,
                Kardex.warehouse_id == location.warehouse_id,
                Kardex.is_active == True,
            ),
        )
    )

    stock_items = []
    for row in result:
        stock_items.append(WarehouseLocationStockResponse(
            product_id=row.product_id,
            product_codigo=row.codigo_principal,
            product_descripcion=row.descripcion,
            cantidad=row.saldo_cantidad or Decimal("0"),
        ))

    return stock_items


# ==========================================
# Mapa Visual del Almacen
# ==========================================

@router.get(
    "/warehouse/{warehouse_id}/map",
    response_model=WarehouseLocationMapResponse,
)
async def get_warehouse_map(
    warehouse_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener layout visual de ubicaciones de un almacen agrupadas por zona.

    Retorna un diccionario donde cada clave es una zona y el valor es la lista
    de ubicaciones en esa zona, facilitando la renderizacion de un mapa visual.
    """
    warehouse_id = validate_uuid(warehouse_id, "warehouse_id")
    warehouse = await _get_warehouse_for_user(db, warehouse_id, current_user.id)

    result = await db.execute(
        select(WarehouseLocation)
        .where(
            WarehouseLocation.warehouse_id == warehouse_id,
            WarehouseLocation.is_active == True,
        )
        .order_by(
            WarehouseLocation.zona,
            WarehouseLocation.pasillo.nulls_first(),
            WarehouseLocation.rack.nulls_first(),
            WarehouseLocation.estante.nulls_first(),
        )
    )
    locations = result.scalars().all()

    # Agrupar por zona
    zonas: dict[str, list[WarehouseLocationResponse]] = {}
    total_ubicaciones = 0
    ubicaciones_disponibles = 0

    for loc in locations:
        total_ubicaciones += 1
        if loc.producto_id is None:
            ubicaciones_disponibles += 1

        if loc.zona not in zonas:
            zonas[loc.zona] = []
        zonas[loc.zona].append(WarehouseLocationResponse.model_validate(loc))

    return WarehouseLocationMapResponse(
        warehouse_id=warehouse.id,
        warehouse_nombre=warehouse.nombre,
        zonas=zonas,
        total_ubicaciones=total_ubicaciones,
        ubicaciones_disponibles=ubicaciones_disponibles,
    )

"""
ContaEC - Endpoints de Productos/Servicios
CRUD de productos y servicios para facturación electrónica
con impuestos según catálogos del SRI (Tabla 16 IVA, Tabla 18 ICE)
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.validation import clean_company_id, validate_uuid
from app.core.security import get_current_user
from app.models.company import Company
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["Productos"])


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

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crear un nuevo producto o servicio para la empresa del usuario.

    Verifica que la empresa pertenezca al usuario antes de crear el producto.
    Valida el límite de productos según el plan de licencia.
    """
    data.company_id = validate_uuid(data.company_id, "company_id")
    # Verificar que la empresa pertenece al usuario
    await _get_company_for_user(db, data.company_id, current_user.id)

    # Validar límite de productos según licencia
    from app.core.utils import get_license_limits

    limits = get_license_limits(current_user)
    max_products = limits['max_products']

    # Contar productos activos en la empresa
    result = await db.execute(
        select(func.count(Product.id)).where(
            Product.company_id == data.company_id,
            Product.is_active == True
        )
    )
    current_count = result.scalar() or 0

    if current_count >= max_products:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Límite de productos alcanzado en esta empresa. Tu plan actual permite {max_products} producto(s). "
                   f"Contacta a soporte para actualizar tu licencia."
        )

    # Verificar que no exista un producto con el mismo código principal en la empresa
    result = await db.execute(
        select(Product).where(
            Product.company_id == data.company_id,
            Product.codigo_principal == data.codigo_principal,
            Product.is_active == True,
        )
    )
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un producto con el código '{data.codigo_principal}' en esta empresa.",
        )
    
    # Crear producto
    product = Product(
        company_id=data.company_id,
        codigo_principal=data.codigo_principal,
        codigo_auxiliar=data.codigo_auxiliar,
        descripcion=data.descripcion,
        tipo=data.tipo,
        precio_unitario=data.precio_unitario,
        iva_codigo=data.iva_codigo,
        iva_porcentaje=data.iva_porcentaje,
        iva_incluido=data.iva_incluido,
        ice_codigo=data.ice_codigo,
        ice_porcentaje=data.ice_porcentaje,
        valor_ice_unitario=data.valor_ice_unitario,
        valor_irbpnr=data.valor_irbpnr,
        subsidio=data.subsidio,
        categoria=data.categoria,
        detalle=data.detalle,
        imagen=data.imagen,
        unidad_medida=data.unidad_medida,
        descuento=data.descuento,
    )
    db.add(product)
    await db.flush()
    
    logger.info(
        f"Producto creado: código={data.codigo_principal}, "
        f"empresa={data.company_id}"
    )
    
    return ProductResponse.model_validate(product)


@router.get("", response_model=list[ProductResponse])
async def list_products(
    company_id: str | None = None,
    tipo: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar productos de las empresas del usuario.

    Opcionalmente filtrado por empresa, tipo (B/S) y estado activo.
    """
    company_id = clean_company_id(company_id)
    try:
        # Consulta base: productos de empresas del usuario
        query = (
            select(Product)
            .join(Company, Product.company_id == Company.id)
            .where(Company.user_id == current_user.id)
        )

        # Filtro de empresa
        if company_id:
            await _get_company_for_user(db, company_id, current_user.id)
            query = query.where(Product.company_id == company_id)

        # Filtro de tipo (B=Bien, S=Servicio)
        if tipo:
            query = query.where(Product.tipo == tipo)

        # Filtro de estado activo
        if is_active is not None:
            query = query.where(Product.is_active == is_active)

        # Ordenar por descripción y paginar
        query = query.order_by(Product.descripcion).offset(skip).limit(limit)

        result = await db.execute(query)
        products = result.scalars().all()

        return [ProductResponse.model_validate(p) for p in products]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing products: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar productos: {str(e)}",
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un producto específico por su ID"""
    product_id = validate_uuid(product_id, "product_id")
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )
    
    # Verificar que la empresa pertenezca al usuario
    await _get_company_for_user(db, product.company_id, current_user.id)
    
    return ProductResponse.model_validate(product)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    data: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar datos de un producto o servicio"""
    product_id = validate_uuid(product_id, "product_id")
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )
    
    # Verificar que la empresa pertenezca al usuario
    await _get_company_for_user(db, product.company_id, current_user.id)
    
    # Si se cambia el código principal, verificar que no exista otro con el mismo código
    if data.codigo_principal and data.codigo_principal != product.codigo_principal:
        existing = await db.execute(
            select(Product).where(
                Product.company_id == product.company_id,
                Product.codigo_principal == data.codigo_principal,
                Product.id != product_id,
                Product.is_active == True,
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe un producto con el código '{data.codigo_principal}' en esta empresa.",
            )
    
    # Actualizar campos proporcionados
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    
    await db.flush()
    
    logger.info(f"Producto actualizado: código={product.codigo_principal}")
    
    return ProductResponse.model_validate(product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Desactivar un producto (eliminación lógica).
    
    Los productos usados en comprobantes existentes no se eliminan
    físicamente para mantener la integridad referencial.
    """
    product_id = validate_uuid(product_id, "product_id")
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalars().first()
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )
    
    # Verificar que la empresa pertenezca al usuario
    await _get_company_for_user(db, product.company_id, current_user.id)
    
    # Eliminación lógica
    product.is_active = False
    await db.flush()
    
    logger.info(f"Producto desactivado: código={product.codigo_principal}")
    
    return {"message": "Producto desactivado exitosamente."}

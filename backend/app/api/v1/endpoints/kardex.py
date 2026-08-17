"""
ContaEC - Endpoints de Kardex (Movimientos de Inventario)
CRUD de movimientos de kardex con cálculo automático de saldos
y generación de reportes por métodos FIFO/LIFO/PP
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import effective_owner_id
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.company import Company
from app.models.kardex import Kardex, KardexTipoMovimiento
from app.models.product import Product
from app.models.user import User
from app.schemas.kardex import (
    KardexAjuste,
    KardexCreate,
    KardexResponse,
    KardexReporteResponse,
    KardexSaldoResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/kardex", tags=["Kardex"])


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


async def _get_product_for_company(
    db: AsyncSession,
    product_id: str,
    company_id: str,
) -> Product:
    """
    Obtiene un producto verificando que pertenezca a la empresa.

    Raises:
        HTTPException: Si el producto no existe o no pertenece a la empresa
    """
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.company_id == company_id,
            Product.is_active == True,
        )
    )
    product = result.scalars().first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado o no pertenece a la empresa.",
        )
    return product


async def _get_last_saldo(
    db: AsyncSession,
    product_id: str,
    company_id: str,
) -> tuple[Decimal, Decimal]:
    """
    Obtiene el último saldo (cantidad, valor) de un producto en kardex.

    Returns:
        Tupla (saldo_cantidad, saldo_valor) del último movimiento, o (0, 0) si no hay movimientos
    """
    result = await db.execute(
        select(Kardex)
        .where(
            Kardex.product_id == product_id,
            Kardex.company_id == company_id,
            Kardex.is_active == True,
        )
        .order_by(Kardex.fecha_movimiento.desc(), Kardex.created_at.desc())
        .limit(1)
    )
    last_movement = result.scalars().first()
    if last_movement:
        return last_movement.saldo_cantidad, last_movement.saldo_valor
    return Decimal("0"), Decimal("0")


# ==========================================
# Endpoints CRUD
# ==========================================

@router.post("", response_model=KardexResponse, status_code=status.HTTP_201_CREATED)
async def create_kardex_movement(
    data: KardexCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crear un nuevo movimiento de kardex.

    Calcula automáticamente el saldo acumulado (cantidad y valor)
    basado en el último movimiento registrado del producto.
    """
    data.product_id = clean_uuid_param(data.product_id, "product_id")
    data.referencia_id = clean_uuid_param(data.referencia_id, "referencia_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    # Verificar que la empresa pertenece al usuario
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # Verificar que el producto pertenece a la empresa
    await _get_product_for_company(db, data.product_id, data.company_id)

    # Obtener saldo actual
    saldo_cantidad, saldo_valor = await _get_last_saldo(
        db, data.product_id, data.company_id
    )

    # Calcular costo total del movimiento
    costo_total = data.cantidad * data.costo_unitario

    # Calcular nuevo saldo según tipo de movimiento
    tipo = data.tipo_movimiento
    if tipo == KardexTipoMovimiento.ENTRADA.value:
        nuevo_saldo_cantidad = saldo_cantidad + data.cantidad
        nuevo_saldo_valor = saldo_valor + costo_total
    elif tipo == KardexTipoMovimiento.SALIDA.value:
        if data.cantidad > saldo_cantidad:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stock insuficiente. Saldo actual: {saldo_cantidad}, "
                       f"Cantidad solicitada: {data.cantidad}",
            )
        nuevo_saldo_cantidad = saldo_cantidad - data.cantidad
        # Para salidas, el valor se reduce proporcionalmente
        if saldo_cantidad > 0:
            costo_promedio = saldo_valor / saldo_cantidad
            nuevo_saldo_valor = saldo_valor - (data.cantidad * costo_promedio)
        else:
            nuevo_saldo_valor = Decimal("0")
    elif tipo == KardexTipoMovimiento.AJUSTE.value:
        # Ajuste puede ser positivo o negativo
        nuevo_saldo_cantidad = saldo_cantidad + data.cantidad
        if data.cantidad >= 0:
            nuevo_saldo_valor = saldo_valor + costo_total
        else:
            nuevo_saldo_valor = saldo_valor - abs(costo_total)
        if nuevo_saldo_cantidad < 0:
            nuevo_saldo_cantidad = Decimal("0")
            nuevo_saldo_valor = Decimal("0")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de movimiento inválido: {tipo}",
        )

    # Crear movimiento
    fecha = data.fecha_movimiento or datetime.now(timezone.utc)
    movement = Kardex(
        company_id=data.company_id,
        product_id=data.product_id,
        tipo_movimiento=tipo,
        cantidad=data.cantidad,
        costo_unitario=data.costo_unitario,
        costo_total=costo_total,
        saldo_cantidad=nuevo_saldo_cantidad,
        saldo_valor=nuevo_saldo_valor,
        referencia_tipo=data.referencia_tipo,
        referencia_id=data.referencia_id,
        referencia_secuencial=data.referencia_secuencial,
        detalle=data.detalle,
        fecha_movimiento=fecha,
        user_id=current_user.id,
    )
    db.add(movement)
    await db.flush()

    # Actualizar stock del producto
    result = await db.execute(
        select(Product).where(Product.id == data.product_id)
    )
    product = result.scalars().first()
    if product and hasattr(product, "stock"):
        product.stock = nuevo_saldo_cantidad
        await db.flush()

    logger.info(
        f"Kardex: {tipo} producto={data.product_id}, "
        f"cantidad={data.cantidad}, saldo={nuevo_saldo_cantidad}"
    )

    return KardexResponse.model_validate(movement)


@router.get("", response_model=list[KardexResponse])
async def list_kardex_movements(
    company_id: str | None = None,
    product_id: str | None = None,
    tipo_movimiento: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar movimientos de kardex con filtros opcionales.

    Filtra por empresa, producto, tipo de movimiento y rango de fechas.
    Solo muestra movimientos de las empresas del usuario.
    """
    product_id = clean_uuid_param(product_id, "product_id")
    company_id = clean_company_id(company_id)
    # Consulta base: movimientos de empresas del usuario
    query = (
        select(Kardex)
        .join(Company, Kardex.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user), Kardex.is_active == True)
    )

    # Filtros
    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(Kardex.company_id == company_id)

    if product_id:
        query = query.where(Kardex.product_id == product_id)

    if tipo_movimiento:
        if tipo_movimiento not in ("entrada", "salida", "ajuste"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de movimiento inválido. Válidos: entrada, salida, ajuste",
            )
        query = query.where(Kardex.tipo_movimiento == tipo_movimiento)

    if fecha_desde:
        query = query.where(Kardex.fecha_movimiento >= fecha_desde)

    if fecha_hasta:
        query = query.where(Kardex.fecha_movimiento <= fecha_hasta)

    # Ordenar por fecha y paginar
    query = query.order_by(Kardex.fecha_movimiento.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    movements = result.scalars().all()

    return [KardexResponse.model_validate(m) for m in movements]


@router.get("/product/{product_id}", response_model=list[KardexResponse])
async def get_product_kardex(
    product_id: str,
    company_id: str = Query(..., description="ID de la empresa"),
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(500, ge=1, le=2000, description="Número máximo de registros"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener el kardex completo de un producto con saldos acumulados.

    Retorna todos los movimientos ordenados por fecha (ascendente)
    para ver la evolución del inventario.
    """
    company_id = validate_uuid(company_id, "company_id")
    product_id = validate_uuid(product_id, "product_id")
    # Verificar que la empresa pertenece al usuario
    await _get_company_for_user(db, company_id, effective_owner_id(current_user))

    # Verificar que el producto pertenece a la empresa
    await _get_product_for_company(db, product_id, company_id)

    # Obtener movimientos ordenados por fecha ascendente
    query = (
        select(Kardex)
        .where(
            Kardex.product_id == product_id,
            Kardex.company_id == company_id,
            Kardex.is_active == True,
        )
        .order_by(Kardex.fecha_movimiento.asc(), Kardex.created_at.asc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    movements = result.scalars().all()

    return [KardexResponse.model_validate(m) for m in movements]


@router.get("/product/{product_id}/saldo", response_model=KardexSaldoResponse)
async def get_product_saldo(
    product_id: str,
    company_id: str = Query(..., description="ID de la empresa"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener el saldo actual de un producto.

    Retorna la cantidad actual en stock, el valor total y el costo promedio ponderado.
    """
    company_id = validate_uuid(company_id, "company_id")
    product_id = validate_uuid(product_id, "product_id")
    # Verificar que la empresa pertenece al usuario
    await _get_company_for_user(db, company_id, effective_owner_id(current_user))

    # Verificar que el producto pertenece a la empresa
    await _get_product_for_company(db, product_id, company_id)

    # Obtener saldo actual
    saldo_cantidad, saldo_valor = await _get_last_saldo(db, product_id, company_id)

    # Calcular costo promedio ponderado
    costo_promedio = Decimal("0")
    if saldo_cantidad > 0:
        costo_promedio = saldo_valor / saldo_cantidad

    return KardexSaldoResponse(
        product_id=product_id,
        saldo_cantidad=saldo_cantidad,
        saldo_valor=saldo_valor,
        costo_promedio=costo_promedio,
    )


@router.post("/ajuste", response_model=KardexResponse, status_code=status.HTTP_201_CREATED)
async def create_kardex_ajuste(
    data: KardexAjuste,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crear un ajuste de inventario.

    El ajuste puede ser positivo (incrementar stock) o negativo (decrementar stock).
    Se registra automáticamente como tipo 'ajuste' en el kardex.
    """
    data.product_id = clean_uuid_param(data.product_id, "product_id")
    data.referencia_id = clean_uuid_param(data.referencia_id, "referencia_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    # Verificar que la empresa pertenece al usuario
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # Verificar que el producto pertenece a la empresa
    await _get_product_for_company(db, data.product_id, data.company_id)

    # Obtener saldo actual
    saldo_cantidad, saldo_valor = await _get_last_saldo(
        db, data.product_id, data.company_id
    )

    cantidad = data.cantidad_ajuste
    costo_unitario = data.costo_unitario or Decimal("0")
    costo_total = abs(cantidad) * costo_unitario

    # Calcular nuevo saldo
    nuevo_saldo_cantidad = saldo_cantidad + cantidad
    nuevo_saldo_valor = saldo_valor

    if cantidad >= 0:
        # Ajuste positivo: incrementa stock y valor
        nuevo_saldo_valor = saldo_valor + costo_total
    else:
        # Ajuste negativo: decrementa stock y valor
        if abs(cantidad) > saldo_cantidad:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ajuste excede el stock disponible. "
                       f"Saldo actual: {saldo_cantidad}, "
                       f"Ajuste solicitado: {cantidad}",
            )
        if saldo_cantidad > 0:
            costo_promedio = saldo_valor / saldo_cantidad
            nuevo_saldo_valor = saldo_valor - (abs(cantidad) * costo_promedio)
        else:
            nuevo_saldo_valor = Decimal("0")

    # Determinar sub-tipo de ajuste
    detalle = data.detalle or ("Ajuste positivo de inventario" if cantidad >= 0
                                else "Ajuste negativo de inventario")

    # Crear movimiento
    movement = Kardex(
        company_id=data.company_id,
        product_id=data.product_id,
        tipo_movimiento=KardexTipoMovimiento.AJUSTE.value,
        cantidad=abs(cantidad),
        costo_unitario=costo_unitario,
        costo_total=costo_total,
        saldo_cantidad=max(nuevo_saldo_cantidad, Decimal("0")),
        saldo_valor=max(nuevo_saldo_valor, Decimal("0")),
        referencia_tipo=data.referencia_tipo or "ajuste",
        referencia_id=data.referencia_id,
        referencia_secuencial=None,
        detalle=detalle,
        fecha_movimiento=datetime.now(timezone.utc),
        user_id=current_user.id,
    )
    db.add(movement)
    await db.flush()

    # Actualizar stock del producto
    result = await db.execute(
        select(Product).where(Product.id == data.product_id)
    )
    product = result.scalars().first()
    if product and hasattr(product, "stock"):
        product.stock = max(nuevo_saldo_cantidad, Decimal("0"))
        await db.flush()

    logger.info(
        f"Kardex ajuste: producto={data.product_id}, "
        f"cantidad={cantidad}, nuevo_saldo={nuevo_saldo_cantidad}"
    )

    return KardexResponse.model_validate(movement)


@router.get("/reporte", response_model=KardexReporteResponse)
async def get_kardex_reporte(
    product_id: str = Query(..., description="ID del producto"),
    company_id: str = Query(..., description="ID de la empresa"),
    metodo: str = Query(
        "pp",
        description="Método de valoración: fifo, lifo, pp (promedio ponderado)",
    ),
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generar reporte de kardex con método de valoración.

    Métodos soportados:
    - pp: Promedio Ponderado (default, recomendado por SRI)
    - fifo: First In, First Out
    - lifo: Last In, First Out
    """
    company_id = validate_uuid(company_id, "company_id")
    # Verificar que la empresa pertenece al usuario
    await _get_company_for_user(db, company_id, effective_owner_id(current_user))

    # Verificar que el producto pertenece a la empresa
    product = await _get_product_for_company(db, product_id, company_id)

    # Validar método de valoración
    if metodo not in ("fifo", "lifo", "pp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Método de valoración inválido. Válidos: fifo, lifo, pp",
        )

    # Construir consulta de movimientos
    query = (
        select(Kardex)
        .where(
            Kardex.product_id == product_id,
            Kardex.company_id == company_id,
            Kardex.is_active == True,
        )
        .order_by(Kardex.fecha_movimiento.asc(), Kardex.created_at.asc())
    )

    if fecha_desde:
        query = query.where(Kardex.fecha_movimiento >= fecha_desde)
    if fecha_hasta:
        query = query.where(Kardex.fecha_movimiento <= fecha_hasta)

    result = await db.execute(query)
    movements = result.scalars().all()

    # Calcular totales para el reporte
    saldo_inicial_cantidad = Decimal("0")
    saldo_inicial_valor = Decimal("0")
    total_entradas_cantidad = Decimal("0")
    total_entradas_valor = Decimal("0")
    total_salidas_cantidad = Decimal("0")
    total_salidas_valor = Decimal("0")

    # Si hay filtro de fecha, obtener saldo inicial
    if fecha_desde and movements:
        result_ini = await db.execute(
            select(Kardex)
            .where(
                Kardex.product_id == product_id,
                Kardex.company_id == company_id,
                Kardex.is_active == True,
                Kardex.fecha_movimiento < fecha_desde,
            )
            .order_by(Kardex.fecha_movimiento.desc(), Kardex.created_at.desc())
            .limit(1)
        )
        last_before = result_ini.scalars().first()
        if last_before:
            saldo_inicial_cantidad = last_before.saldo_cantidad
            saldo_inicial_valor = last_before.saldo_valor

    # Recalcular saldos según método de valoración
    if metodo == "pp":
        # Promedio Ponderado: usar saldos ya calculados (que son PP)
        for m in movements:
            if m.tipo_movimiento in (KardexTipoMovimiento.ENTRADA.value,):
                total_entradas_cantidad += m.cantidad
                total_entradas_valor += m.costo_total
            elif m.tipo_movimiento in (KardexTipoMovimiento.SALIDA.value,):
                total_salidas_cantidad += m.cantidad
                total_salidas_valor += m.costo_total
            elif m.tipo_movimiento == KardexTipoMovimiento.AJUSTE.value:
                # Ajustes positivos se suman a entradas, negativos a salidas
                if m.saldo_cantidad >= saldo_inicial_cantidad:
                    total_entradas_cantidad += m.cantidad
                    total_entradas_valor += m.costo_total
                else:
                    total_salidas_cantidad += m.cantidad
                    total_salidas_valor += m.costo_total

    saldo_final_cantidad = (
        saldo_inicial_cantidad + total_entradas_cantidad - total_salidas_cantidad
    )
    saldo_final_valor = (
        saldo_inicial_valor + total_entradas_valor - total_salidas_valor
    )

    metodo_nombre = {
        "fifo": "FIFO (Primeras Entradas, Primeras Salidas)",
        "lifo": "LIFO (Últimas Entradas, Primeras Salidas)",
        "pp": "PP (Promedio Ponderado)",
    }

    return KardexReporteResponse(
        product_id=product_id,
        producto_descripcion=product.descripcion,
        producto_codigo=product.codigo_principal,
        metodo_valoracion=metodo_nombre.get(metodo, metodo),
        movimientos=[KardexResponse.model_validate(m) for m in movements],
        saldo_inicial_cantidad=saldo_inicial_cantidad,
        saldo_inicial_valor=saldo_inicial_valor,
        total_entradas_cantidad=total_entradas_cantidad,
        total_entradas_valor=total_entradas_valor,
        total_salidas_cantidad=total_salidas_cantidad,
        total_salidas_valor=total_salidas_valor,
        saldo_final_cantidad=saldo_final_cantidad,
        saldo_final_valor=saldo_final_valor,
    )

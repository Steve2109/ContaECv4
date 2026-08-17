"""
ContaEC - Endpoints de Compras
Órdenes de compra, recepciones de mercadería, cuentas por pagar y retenciones de compra
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_action
from app.core.permissions import effective_owner_id
from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.company import Company
from app.models.purchase import (
    CuentaPorPagar,
    OrdenCompra,
    OrdenCompraDetalle,
    RecepcionMercaderia,
    RecepcionMercaderiaDetalle,
    RetencionCompra,
)
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.purchase import (
    CuentaPorPagarCreate,
    CuentaPorPagarResponse,
    CuentaPorPagarUpdate,
    OrdenCompraCreate,
    OrdenCompraResponse,
    OrdenCompraUpdate,
    RecepcionMercaderiaCreate,
    RecepcionMercaderiaResponse,
    RecepcionMercaderiaUpdate,
    RetencionCompraCreate,
    RetencionCompraResponse,
    RetencionCompraUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/purchases", tags=["Compras"])


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


# ==========================================
# Órdenes de Compra
# ==========================================

@router.post("/ordenes", response_model=OrdenCompraResponse, status_code=status.HTTP_201_CREATED)
async def create_orden_compra(
    data: OrdenCompraCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva orden de compra"""
    data.supplier_id = clean_uuid_param(data.supplier_id, "supplier_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # Verificar proveedor
    supplier_result = await db.execute(
        select(Supplier).where(Supplier.id == data.supplier_id, Supplier.is_active == True)
    )
    if not supplier_result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proveedor no encontrado.",
        )

    # Generar número secuencial
    numero = await _get_next_number(db, data.company_id, "OC", OrdenCompra)

    # Calcular totales
    subtotal = Decimal("0")
    total_iva = Decimal("0")

    detalles = []
    for det in data.detalles:
        precio_total = det.cantidad * det.precio_unitario - det.descuento
        iva_valor = precio_total * det.iva_porcentaje / Decimal("100")
        subtotal += precio_total
        total_iva += iva_valor
        detalles.append(OrdenCompraDetalle(
            product_id=det.product_id,
            codigo_principal=det.codigo_principal,
            descripcion=det.descripcion,
            cantidad=det.cantidad,
            precio_unitario=det.precio_unitario,
            iva_codigo=det.iva_codigo,
            iva_porcentaje=det.iva_porcentaje,
            descuento=det.descuento,
            precio_total=precio_total,
        ))

    total_con_impuestos = subtotal + total_iva

    orden = OrdenCompra(
        company_id=data.company_id,
        supplier_id=data.supplier_id,
        user_id=current_user.id,
        numero=numero,
        fecha_emision=data.fecha_emision,
        fecha_entrega_estimada=data.fecha_entrega_estimada,
        subtotal_sin_impuestos=subtotal,
        total_iva=total_iva,
        total_con_impuestos=total_con_impuestos,
        observaciones=data.observaciones,
        detalles=detalles,
    )
    db.add(orden)
    await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="orden_compra",
        entity_id=orden.id,
        description=f"Orden de compra creada: {numero}",
        ip_address=request.client.host if request.client else None,
    )

    return OrdenCompraResponse.model_validate(orden)


@router.get("/ordenes", response_model=list[OrdenCompraResponse])
async def list_ordenes_compra(
    company_id: str | None = None,
    supplier_id: str | None = None,
    estado: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar órdenes de compra"""
    supplier_id = clean_uuid_param(supplier_id, "supplier_id")
    company_id = clean_company_id(company_id)
    query = (
        select(OrdenCompra)
        .join(Company, OrdenCompra.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
    )

    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(OrdenCompra.company_id == company_id)
    if supplier_id:
        query = query.where(OrdenCompra.supplier_id == supplier_id)
    if estado:
        query = query.where(OrdenCompra.estado == estado)
    if is_active is not None:
        query = query.where(OrdenCompra.is_active == is_active)

    query = query.order_by(OrdenCompra.fecha_emision.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    ordenes = result.scalars().all()
    return [OrdenCompraResponse.model_validate(o) for o in ordenes]


@router.get("/ordenes/{orden_id}", response_model=OrdenCompraResponse)
async def get_orden_compra(
    orden_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una orden de compra específica"""
    orden_id = validate_uuid(orden_id, "orden_id")
    result = await db.execute(
        select(OrdenCompra).where(OrdenCompra.id == orden_id)
    )
    orden = result.scalars().first()
    if not orden:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de compra no encontrada.")
    await _get_company_for_user(db, orden.company_id, effective_owner_id(current_user))
    return OrdenCompraResponse.model_validate(orden)


@router.put("/ordenes/{orden_id}", response_model=OrdenCompraResponse)
async def update_orden_compra(
    orden_id: str,
    data: OrdenCompraUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una orden de compra"""
    orden_id = validate_uuid(orden_id, "orden_id")
    result = await db.execute(
        select(OrdenCompra).where(OrdenCompra.id == orden_id)
    )
    orden = result.scalars().first()
    if not orden:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de compra no encontrada.")
    await _get_company_for_user(db, orden.company_id, effective_owner_id(current_user))

    if orden.estado != "borrador":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden modificar órdenes en estado borrador.",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(orden, field, value)

    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="orden_compra", entity_id=orden.id,
        description=f"Orden de compra actualizada: {orden.numero}",
        ip_address=request.client.host if request.client else None,
    )

    return OrdenCompraResponse.model_validate(orden)


@router.delete("/ordenes/{orden_id}")
async def delete_orden_compra(
    orden_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Anular una orden de compra (eliminación lógica)"""
    orden_id = validate_uuid(orden_id, "orden_id")
    result = await db.execute(
        select(OrdenCompra).where(OrdenCompra.id == orden_id)
    )
    orden = result.scalars().first()
    if not orden:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de compra no encontrada.")
    await _get_company_for_user(db, orden.company_id, effective_owner_id(current_user))

    orden.is_active = False
    orden.estado = "anulada"
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="DELETE", entity_type="orden_compra", entity_id=orden.id,
        description=f"Orden de compra anulada: {orden.numero}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Orden de compra anulada exitosamente."}


# ==========================================
# Recepciones de Mercadería
# ==========================================

@router.post("/recepciones", response_model=RecepcionMercaderiaResponse, status_code=status.HTTP_201_CREATED)
async def create_recepcion_mercaderia(
    data: RecepcionMercaderiaCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva recepción de mercadería"""
    data.supplier_id = clean_uuid_param(data.supplier_id, "supplier_id")
    data.orden_compra_id = clean_uuid_param(data.orden_compra_id, "orden_compra_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # Verificar proveedor
    supplier_result = await db.execute(
        select(Supplier).where(Supplier.id == data.supplier_id, Supplier.is_active == True)
    )
    if not supplier_result.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado.")

    # Verificar orden de compra si se proporciona
    if data.orden_compra_id:
        oc_result = await db.execute(
            select(OrdenCompra).where(OrdenCompra.id == data.orden_compra_id)
        )
        oc = oc_result.scalars().first()
        if not oc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden de compra no encontrada.")

    # Generar número secuencial
    numero = await _get_next_number(db, data.company_id, "RM", RecepcionMercaderia)

    # Crear detalles
    detalles = []
    for det in data.detalles:
        precio_total = det.cantidad_recibida * det.precio_unitario
        detalles.append(RecepcionMercaderiaDetalle(
            product_id=det.product_id,
            orden_compra_detalle_id=det.orden_compra_detalle_id,
            codigo_principal=det.codigo_principal,
            descripcion=det.descripcion,
            cantidad_recibida=det.cantidad_recibida,
            cantidad_dañada=det.cantidad_dañada,
            precio_unitario=det.precio_unitario,
            precio_total=precio_total,
        ))

    recepcion = RecepcionMercaderia(
        company_id=data.company_id,
        orden_compra_id=data.orden_compra_id,
        supplier_id=data.supplier_id,
        user_id=current_user.id,
        numero=numero,
        fecha_recepcion=data.fecha_recepcion,
        observaciones=data.observaciones,
        detalles=detalles,
    )
    db.add(recepcion)
    await db.flush()

    # Actualizar cantidades recibidas en la OC si existe
    if data.orden_compra_id:
        for det in data.detalles:
            if det.orden_compra_detalle_id:
                oc_det_result = await db.execute(
                    select(OrdenCompraDetalle).where(
                        OrdenCompraDetalle.id == det.orden_compra_detalle_id
                    )
                )
                oc_det = oc_det_result.scalars().first()
                if oc_det:
                    oc_det.cantidad_recibida = (oc_det.cantidad_recibida or Decimal("0")) + det.cantidad_recibida

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="CREATE", entity_type="recepcion_mercaderia", entity_id=recepcion.id,
        description=f"Recepción de mercadería creada: {numero}",
        ip_address=request.client.host if request.client else None,
    )

    return RecepcionMercaderiaResponse.model_validate(recepcion)


@router.get("/recepciones", response_model=list[RecepcionMercaderiaResponse])
async def list_recepciones(
    company_id: str | None = None,
    supplier_id: str | None = None,
    estado: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar recepciones de mercadería"""
    supplier_id = clean_uuid_param(supplier_id, "supplier_id")
    company_id = clean_company_id(company_id)
    query = (
        select(RecepcionMercaderia)
        .join(Company, RecepcionMercaderia.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
    )

    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(RecepcionMercaderia.company_id == company_id)
    if supplier_id:
        query = query.where(RecepcionMercaderia.supplier_id == supplier_id)
    if estado:
        query = query.where(RecepcionMercaderia.estado == estado)
    if is_active is not None:
        query = query.where(RecepcionMercaderia.is_active == is_active)

    query = query.order_by(RecepcionMercaderia.fecha_recepcion.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    recepciones = result.scalars().all()
    return [RecepcionMercaderiaResponse.model_validate(r) for r in recepciones]


@router.get("/recepciones/{recepcion_id}", response_model=RecepcionMercaderiaResponse)
async def get_recepcion(
    recepcion_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una recepción de mercadería específica"""
    recepcion_id = validate_uuid(recepcion_id, "recepcion_id")
    result = await db.execute(
        select(RecepcionMercaderia).where(RecepcionMercaderia.id == recepcion_id)
    )
    recepcion = result.scalars().first()
    if not recepcion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recepción no encontrada.")
    await _get_company_for_user(db, recepcion.company_id, effective_owner_id(current_user))
    return RecepcionMercaderiaResponse.model_validate(recepcion)


@router.put("/recepciones/{recepcion_id}", response_model=RecepcionMercaderiaResponse)
async def update_recepcion(
    recepcion_id: str,
    data: RecepcionMercaderiaUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una recepción de mercadería"""
    recepcion_id = validate_uuid(recepcion_id, "recepcion_id")
    result = await db.execute(
        select(RecepcionMercaderia).where(RecepcionMercaderia.id == recepcion_id)
    )
    recepcion = result.scalars().first()
    if not recepcion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recepción no encontrada.")
    await _get_company_for_user(db, recepcion.company_id, effective_owner_id(current_user))

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(recepcion, field, value)

    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="recepcion_mercaderia", entity_id=recepcion.id,
        description=f"Recepción actualizada: {recepcion.numero}",
        ip_address=request.client.host if request.client else None,
    )

    return RecepcionMercaderiaResponse.model_validate(recepcion)


@router.delete("/recepciones/{recepcion_id}")
async def delete_recepcion(
    recepcion_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Desactivar una recepción de mercadería"""
    recepcion_id = validate_uuid(recepcion_id, "recepcion_id")
    result = await db.execute(
        select(RecepcionMercaderia).where(RecepcionMercaderia.id == recepcion_id)
    )
    recepcion = result.scalars().first()
    if not recepcion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recepción no encontrada.")
    await _get_company_for_user(db, recepcion.company_id, effective_owner_id(current_user))

    recepcion.is_active = False
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="DELETE", entity_type="recepcion_mercaderia", entity_id=recepcion.id,
        description=f"Recepción desactivada: {recepcion.numero}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Recepción desactivada exitosamente."}


# ==========================================
# Cuentas por Pagar
# ==========================================

@router.post("/cuentas-por-pagar", response_model=CuentaPorPagarResponse, status_code=status.HTTP_201_CREATED)
async def create_cuenta_por_pagar(
    data: CuentaPorPagarCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva cuenta por pagar"""
    data.supplier_id = clean_uuid_param(data.supplier_id, "supplier_id")
    data.comprobante_id = clean_uuid_param(data.comprobante_id, "comprobante_id")
    data.orden_compra_id = clean_uuid_param(data.orden_compra_id, "orden_compra_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # Verificar proveedor
    supplier_result = await db.execute(
        select(Supplier).where(Supplier.id == data.supplier_id, Supplier.is_active == True)
    )
    if not supplier_result.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado.")

    # Calcular fecha de vencimiento si no se proporciona
    fecha_vencimiento = data.fecha_vencimiento
    if not fecha_vencimiento and data.dias_credito > 0:
        from datetime import timedelta
        fecha_vencimiento = data.fecha_emision + timedelta(days=data.dias_credito)

    cuenta = CuentaPorPagar(
        company_id=data.company_id,
        supplier_id=data.supplier_id,
        user_id=current_user.id,
        comprobante_id=data.comprobante_id,
        orden_compra_id=data.orden_compra_id,
        numero_factura=data.numero_factura,
        fecha_emision=data.fecha_emision,
        fecha_vencimiento=fecha_vencimiento,
        monto_total=data.monto_total,
        monto_pagado=Decimal("0"),
        monto_pendiente=data.monto_total,
        dias_credito=data.dias_credito,
        observaciones=data.observaciones,
    )
    db.add(cuenta)
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="CREATE", entity_type="cuenta_por_pagar", entity_id=cuenta.id,
        description=f"Cuenta por pagar creada: factura {data.numero_factura or 'N/A'} por USD {data.monto_total}",
        ip_address=request.client.host if request.client else None,
    )

    return CuentaPorPagarResponse.model_validate(cuenta)


@router.get("/cuentas-por-pagar", response_model=list[CuentaPorPagarResponse])
async def list_cuentas_por_pagar(
    company_id: str | None = None,
    supplier_id: str | None = None,
    estado: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar cuentas por pagar"""
    supplier_id = clean_uuid_param(supplier_id, "supplier_id")
    company_id = clean_company_id(company_id)
    query = (
        select(CuentaPorPagar)
        .join(Company, CuentaPorPagar.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
    )

    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(CuentaPorPagar.company_id == company_id)
    if supplier_id:
        query = query.where(CuentaPorPagar.supplier_id == supplier_id)
    if estado:
        query = query.where(CuentaPorPagar.estado == estado)
    if is_active is not None:
        query = query.where(CuentaPorPagar.is_active == is_active)

    query = query.order_by(CuentaPorPagar.fecha_vencimiento.asc()).offset(skip).limit(limit)

    result = await db.execute(query)
    cuentas = result.scalars().all()
    return [CuentaPorPagarResponse.model_validate(c) for c in cuentas]


@router.get("/cuentas-por-pagar/{cuenta_id}", response_model=CuentaPorPagarResponse)
async def get_cuenta_por_pagar(
    cuenta_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una cuenta por pagar específica"""
    cuenta_id = validate_uuid(cuenta_id, "cuenta_id")
    result = await db.execute(
        select(CuentaPorPagar).where(CuentaPorPagar.id == cuenta_id)
    )
    cuenta = result.scalars().first()
    if not cuenta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta por pagar no encontrada.")
    await _get_company_for_user(db, cuenta.company_id, effective_owner_id(current_user))
    return CuentaPorPagarResponse.model_validate(cuenta)


@router.put("/cuentas-por-pagar/{cuenta_id}", response_model=CuentaPorPagarResponse)
async def update_cuenta_por_pagar(
    cuenta_id: str,
    data: CuentaPorPagarUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una cuenta por pagar (registro de pagos)"""
    cuenta_id = validate_uuid(cuenta_id, "cuenta_id")
    result = await db.execute(
        select(CuentaPorPagar).where(CuentaPorPagar.id == cuenta_id)
    )
    cuenta = result.scalars().first()
    if not cuenta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta por pagar no encontrada.")
    await _get_company_for_user(db, cuenta.company_id, effective_owner_id(current_user))

    # Si se registra un pago
    if data.monto_pagado is not None and data.monto_pagado > 0:
        cuenta.monto_pagado += data.monto_pagado
        cuenta.monto_pendiente = cuenta.monto_total - cuenta.monto_pagado

        # Actualizar estado según monto pendiente
        if cuenta.monto_pendiente <= 0:
            cuenta.estado = "pagada"
            cuenta.monto_pendiente = Decimal("0")
        else:
            cuenta.estado = "parcial"

    if data.estado:
        cuenta.estado = data.estado
    if data.fecha_vencimiento:
        cuenta.fecha_vencimiento = data.fecha_vencimiento
    if data.observaciones:
        cuenta.observaciones = data.observaciones

    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="cuenta_por_pagar", entity_id=cuenta.id,
        description=f"Cuenta por pagar actualizada: factura {cuenta.numero_factura or 'N/A'}",
        ip_address=request.client.host if request.client else None,
    )

    return CuentaPorPagarResponse.model_validate(cuenta)


@router.delete("/cuentas-por-pagar/{cuenta_id}")
async def delete_cuenta_por_pagar(
    cuenta_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Anular una cuenta por pagar"""
    cuenta_id = validate_uuid(cuenta_id, "cuenta_id")
    result = await db.execute(
        select(CuentaPorPagar).where(CuentaPorPagar.id == cuenta_id)
    )
    cuenta = result.scalars().first()
    if not cuenta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta por pagar no encontrada.")
    await _get_company_for_user(db, cuenta.company_id, effective_owner_id(current_user))

    cuenta.is_active = False
    cuenta.estado = "anulada"
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="DELETE", entity_type="cuenta_por_pagar", entity_id=cuenta.id,
        description=f"Cuenta por pagar anulada: factura {cuenta.numero_factura or 'N/A'}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Cuenta por pagar anulada exitosamente."}


# ==========================================
# Retenciones de Compra
# ==========================================

@router.post("/retenciones", response_model=RetencionCompraResponse, status_code=status.HTTP_201_CREATED)
async def create_retencion_compra(
    data: RetencionCompraCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva retención de compra"""
    data.supplier_id = clean_uuid_param(data.supplier_id, "supplier_id")
    data.cuenta_por_pagar_id = clean_uuid_param(data.cuenta_por_pagar_id, "cuenta_por_pagar_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # Verificar proveedor
    supplier_result = await db.execute(
        select(Supplier).where(Supplier.id == data.supplier_id, Supplier.is_active == True)
    )
    if not supplier_result.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado.")

    # Verificar cuenta por pagar si se proporciona
    if data.cuenta_por_pagar_id:
        cpp_result = await db.execute(
            select(CuentaPorPagar).where(CuentaPorPagar.id == data.cuenta_por_pagar_id)
        )
        if not cpp_result.scalars().first():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta por pagar no encontrada.")

    # Calcular valores de retención
    retencion_iva_valor = (data.base_imponible_iva * data.retencion_iva_porcentaje / Decimal("100")).quantize(Decimal("0.01"))
    retencion_renta_valor = (data.base_imponible_renta * data.retencion_renta_porcentaje / Decimal("100")).quantize(Decimal("0.01"))

    # Generar número secuencial
    numero_result = await db.execute(
        select(func.count(RetencionCompra.id)).where(RetencionCompra.company_id == data.company_id)
    )
    count = numero_result.scalar() or 0
    numero_retencion = f"RET-{str(count + 1).zfill(6)}"

    retencion = RetencionCompra(
        company_id=data.company_id,
        supplier_id=data.supplier_id,
        user_id=current_user.id,
        cuenta_por_pagar_id=data.cuenta_por_pagar_id,
        numero_retencion=numero_retencion,
        fecha_emision=data.fecha_emision,
        base_imponible_iva=data.base_imponible_iva,
        retencion_iva_codigo=data.retencion_iva_codigo,
        retencion_iva_porcentaje=data.retencion_iva_porcentaje,
        retencion_iva_valor=retencion_iva_valor,
        base_imponible_renta=data.base_imponible_renta,
        retencion_renta_codigo=data.retencion_renta_codigo,
        retencion_renta_porcentaje=data.retencion_renta_porcentaje,
        retencion_renta_valor=retencion_renta_valor,
        observaciones=data.observaciones,
    )
    db.add(retencion)
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="CREATE", entity_type="retencion_compra", entity_id=retencion.id,
        description=f"Retención de compra creada: {numero_retencion}",
        ip_address=request.client.host if request.client else None,
    )

    return RetencionCompraResponse.model_validate(retencion)


@router.get("/retenciones", response_model=list[RetencionCompraResponse])
async def list_retenciones(
    company_id: str | None = None,
    supplier_id: str | None = None,
    estado: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar retenciones de compra"""
    supplier_id = clean_uuid_param(supplier_id, "supplier_id")
    company_id = clean_company_id(company_id)
    query = (
        select(RetencionCompra)
        .join(Company, RetencionCompra.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
    )

    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(RetencionCompra.company_id == company_id)
    if supplier_id:
        query = query.where(RetencionCompra.supplier_id == supplier_id)
    if estado:
        query = query.where(RetencionCompra.estado == estado)
    if is_active is not None:
        query = query.where(RetencionCompra.is_active == is_active)

    query = query.order_by(RetencionCompra.fecha_emision.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    retenciones = result.scalars().all()
    return [RetencionCompraResponse.model_validate(r) for r in retenciones]


@router.get("/retenciones/{retencion_id}", response_model=RetencionCompraResponse)
async def get_retencion(
    retencion_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una retención de compra específica"""
    retencion_id = validate_uuid(retencion_id, "retencion_id")
    result = await db.execute(
        select(RetencionCompra).where(RetencionCompra.id == retencion_id)
    )
    retencion = result.scalars().first()
    if not retencion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retención no encontrada.")
    await _get_company_for_user(db, retencion.company_id, effective_owner_id(current_user))
    return RetencionCompraResponse.model_validate(retencion)


@router.put("/retenciones/{retencion_id}", response_model=RetencionCompraResponse)
async def update_retencion(
    retencion_id: str,
    data: RetencionCompraUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una retención de compra"""
    retencion_id = validate_uuid(retencion_id, "retencion_id")
    result = await db.execute(
        select(RetencionCompra).where(RetencionCompra.id == retencion_id)
    )
    retencion = result.scalars().first()
    if not retencion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retención no encontrada.")
    await _get_company_for_user(db, retencion.company_id, effective_owner_id(current_user))

    if retencion.estado != "borrador":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden modificar retenciones en estado borrador.",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(retencion, field, value)

    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="retencion_compra", entity_id=retencion.id,
        description=f"Retención actualizada: {retencion.numero_retencion}",
        ip_address=request.client.host if request.client else None,
    )

    return RetencionCompraResponse.model_validate(retencion)


@router.delete("/retenciones/{retencion_id}")
async def delete_retencion(
    retencion_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Desactivar una retención de compra"""
    retencion_id = validate_uuid(retencion_id, "retencion_id")
    result = await db.execute(
        select(RetencionCompra).where(RetencionCompra.id == retencion_id)
    )
    retencion = result.scalars().first()
    if not retencion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retención no encontrada.")
    await _get_company_for_user(db, retencion.company_id, effective_owner_id(current_user))

    retencion.is_active = False
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="DELETE", entity_type="retencion_compra", entity_id=retencion.id,
        description=f"Retención desactivada: {retencion.numero_retencion}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Retención desactivada exitosamente."}

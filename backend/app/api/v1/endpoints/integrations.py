"""
ContaEC - Endpoints de Integraciones
Integracion bancaria (extractos, conciliacion) y conectores e-commerce
"""
import csv
import io
import logging
from datetime import date as date_cls
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import log_action
from app.core.permissions import effective_owner_id
from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.company import Company
from app.models.integration import (
    CuentaBancaria,
    EcommerceConnector,
    EcommerceSyncLog,
    ExtractoBancario,
    ExtractoEstado,
    MovimientoBancario,
    ConciliacionEstado,
    MovimientoTipo,
    ConnectorEstado,
    SyncEstado,
    BancoTipoCuenta,
    EcommercePlataforma,
)
from app.models.user import User
from app.schemas.integration import (
    CuentaBancariaCreate,
    CuentaBancariaUpdate,
    CuentaBancariaResponse,
    ExtractoBancarioCreate,
    ExtractoBancarioResponse,
    MovimientoBancarioCreate,
    MovimientoBancarioUpdate,
    MovimientoBancarioResponse,
    EcommerceConnectorCreate,
    EcommerceConnectorUpdate,
    EcommerceConnectorResponse,
    EcommerceSyncLogCreate,
    EcommerceSyncLogResponse,
    IntegrationStats,
    EcommerceSyncProductsResponse,
    EcommerceSyncOrdersResponse,
    EcommerceSyncInventoryResponse,
    EcommerceConnectorStatus,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["Integraciones"])


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


# ==========================================
# 1. ESTADISTICAS
# ==========================================

@router.get("/stats", response_model=IntegrationStats)
async def get_integration_stats(
    company_id: str = Query(..., description="ID de la empresa"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener estadisticas generales de integraciones"""
    company_id = validate_uuid(company_id, "company_id")
    await _get_company_for_user(db, company_id, effective_owner_id(current_user))

    # Bank stats
    total_cuentas = await db.execute(
        select(func.count(CuentaBancaria.id)).where(
            CuentaBancaria.company_id == company_id,
        )
    )
    cuentas_activas = await db.execute(
        select(func.count(CuentaBancaria.id)).where(
            CuentaBancaria.company_id == company_id,
            CuentaBancaria.is_active == True,
        )
    )
    total_extractos = await db.execute(
        select(func.count(ExtractoBancario.id)).where(
            ExtractoBancario.company_id == company_id,
        )
    )
    extractos_pendientes = await db.execute(
        select(func.count(ExtractoBancario.id)).where(
            ExtractoBancario.company_id == company_id,
            ExtractoBancario.estado.in_([
                ExtractoEstado.IMPORTADO.value,
                ExtractoEstado.EN_CONCILIACION.value,
            ]),
        )
    )
    mov_pendientes = await db.execute(
        select(func.count(MovimientoBancario.id)).where(
            MovimientoBancario.company_id == company_id,
            MovimientoBancario.conciliacion_estado == ConciliacionEstado.PENDIENTE.value,
        )
    )
    mov_conciliados = await db.execute(
        select(func.count(MovimientoBancario.id)).where(
            MovimientoBancario.company_id == company_id,
            MovimientoBancario.conciliacion_estado == ConciliacionEstado.CONCILIADO.value,
        )
    )
    saldo_total = await db.execute(
        select(func.coalesce(func.sum(CuentaBancaria.saldo_actual), 0)).where(
            CuentaBancaria.company_id == company_id,
            CuentaBancaria.is_active == True,
        )
    )

    # E-Commerce stats
    total_connectors = await db.execute(
        select(func.count(EcommerceConnector.id)).where(
            EcommerceConnector.company_id == company_id,
        )
    )
    connectors_activos = await db.execute(
        select(func.count(EcommerceConnector.id)).where(
            EcommerceConnector.company_id == company_id,
            EcommerceConnector.is_active == True,
            EcommerceConnector.estado == ConnectorEstado.CONECTADO.value,
        )
    )
    # By platform
    platforms_result = await db.execute(
        select(EcommerceConnector.plataforma, func.count(EcommerceConnector.id)).where(
            EcommerceConnector.company_id == company_id,
            EcommerceConnector.is_active == True,
        ).group_by(EcommerceConnector.plataforma)
    )
    platforms = dict(platforms_result.all())

    total_syncs = await db.execute(
        select(func.count(EcommerceSyncLog.id)).where(
            EcommerceSyncLog.company_id == company_id,
        )
    )

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    syncs_hoy = await db.execute(
        select(func.count(EcommerceSyncLog.id)).where(
            EcommerceSyncLog.company_id == company_id,
            EcommerceSyncLog.fecha_inicio >= today,
        )
    )

    ultima_sync = await db.execute(
        select(func.max(EcommerceSyncLog.fecha_inicio)).where(
            EcommerceSyncLog.company_id == company_id,
            EcommerceSyncLog.estado == SyncEstado.COMPLETADA.value,
        )
    )

    return IntegrationStats(
        total_cuentas_bancarias=total_cuentas.scalar() or 0,
        cuentas_activas=cuentas_activas.scalar() or 0,
        total_extractos=total_extractos.scalar() or 0,
        extractos_pendientes=extractos_pendientes.scalar() or 0,
        movimientos_pendientes_conciliar=mov_pendientes.scalar() or 0,
        movimientos_conciliados=mov_conciliados.scalar() or 0,
        saldo_total_cuentas=saldo_total.scalar() or Decimal("0"),
        total_connectors=total_connectors.scalar() or 0,
        connectors_activos=connectors_activos.scalar() or 0,
        connectors_por_plataforma=platforms,
        total_sync_logs=total_syncs.scalar() or 0,
        sync_logs_hoy=syncs_hoy.scalar() or 0,
        ultima_sync_fecha=ultima_sync.scalar(),
    )


# ==========================================
# 2. CUENTAS BANCARIAS CRUD
# ==========================================

@router.post("/bank/accounts", response_model=CuentaBancariaResponse, status_code=status.HTTP_201_CREATED)
async def create_cuenta_bancaria(
    data: CuentaBancariaCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una cuenta bancaria"""
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # Validate tipo_cuenta
    valid_tipos = {t.value for t in BancoTipoCuenta}
    if data.tipo_cuenta not in valid_tipos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de cuenta invalido: {data.tipo_cuenta}",
        )

    cuenta = CuentaBancaria(
        company_id=data.company_id,
        nombre_banco=data.nombre_banco,
        codigo_banco=data.codigo_banco,
        tipo_cuenta=data.tipo_cuenta,
        numero_cuenta=data.numero_cuenta,
        iban=data.iban,
        swift_bic=data.swift_bic,
        titular=data.titular,
        moneda=data.moneda,
        saldo_inicial=data.saldo_inicial,
        saldo_actual=data.saldo_inicial,
        formato_extracto=data.formato_extracto,
        configuracion_mapeo=data.configuracion_mapeo,
    )

    db.add(cuenta)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="cuenta_bancaria",
        entity_id=cuenta.id,
        description=f"Cuenta bancaria creada: {cuenta.nombre_banco} - {cuenta.numero_cuenta}",
        ip_address=request.client.host if request.client else None,
    )

    return CuentaBancariaResponse.model_validate(cuenta)


@router.get("/bank/accounts", response_model=list[CuentaBancariaResponse])
async def list_cuentas_bancarias(
    company_id: str | None = None,
    is_active: bool | None = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar cuentas bancarias"""
    company_id = clean_company_id(company_id)
    try:
        query = (
            select(CuentaBancaria)
            .options(
                selectinload(CuentaBancaria.extractos),
                selectinload(CuentaBancaria.movimientos),
            )
            .join(Company, CuentaBancaria.company_id == Company.id)
            .where(Company.user_id == effective_owner_id(current_user))
        )

        if company_id:
            await _get_company_for_user(db, company_id, effective_owner_id(current_user))
            query = query.where(CuentaBancaria.company_id == company_id)
        if is_active is not None:
            query = query.where(CuentaBancaria.is_active == is_active)

        query = query.order_by(CuentaBancaria.created_at.desc())

        result = await db.execute(query)
        cuentas = result.scalars().all()
        return [CuentaBancariaResponse.model_validate(c) for c in cuentas]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing bank accounts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar cuentas bancarias: {str(e)}",
        )


@router.get("/bank/accounts/{account_id}", response_model=CuentaBancariaResponse)
async def get_cuenta_bancaria(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una cuenta bancaria por ID"""
    account_id = validate_uuid(account_id, "account_id")
    result = await db.execute(
        select(CuentaBancaria).where(CuentaBancaria.id == account_id)
    )
    cuenta = result.scalars().first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada.")
    await _get_company_for_user(db, cuenta.company_id, effective_owner_id(current_user))
    return CuentaBancariaResponse.model_validate(cuenta)


@router.put("/bank/accounts/{account_id}", response_model=CuentaBancariaResponse)
async def update_cuenta_bancaria(
    account_id: str,
    data: CuentaBancariaUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una cuenta bancaria"""
    account_id = validate_uuid(account_id, "account_id")
    result = await db.execute(
        select(CuentaBancaria).where(CuentaBancaria.id == account_id)
    )
    cuenta = result.scalars().first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada.")
    await _get_company_for_user(db, cuenta.company_id, effective_owner_id(current_user))

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cuenta, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="cuenta_bancaria",
        entity_id=cuenta.id,
        description=f"Cuenta bancaria actualizada: {cuenta.nombre_banco}",
        ip_address=request.client.host if request.client else None,
    )

    return CuentaBancariaResponse.model_validate(cuenta)


@router.delete("/bank/accounts/{account_id}")
async def delete_cuenta_bancaria(
    account_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una cuenta bancaria (soft delete)"""
    account_id = validate_uuid(account_id, "account_id")
    result = await db.execute(
        select(CuentaBancaria).where(CuentaBancaria.id == account_id)
    )
    cuenta = result.scalars().first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada.")
    await _get_company_for_user(db, cuenta.company_id, effective_owner_id(current_user))

    cuenta.is_active = False
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="cuenta_bancaria",
        entity_id=account_id,
        description=f"Cuenta bancaria desactivada: {cuenta.nombre_banco}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Cuenta bancaria desactivada exitosamente."}


# ==========================================
# 3. EXTRACTOS BANCARIOS CRUD
# ==========================================

@router.post("/bank/statements", response_model=ExtractoBancarioResponse, status_code=status.HTTP_201_CREATED)
async def create_extracto(
    data: ExtractoBancarioCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear/importar un extracto bancario"""
    data.cuenta_bancaria_id = clean_uuid_param(data.cuenta_bancaria_id, "cuenta_bancaria_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # Verify cuenta bancaria ownership
    cuenta_result = await db.execute(
        select(CuentaBancaria).where(CuentaBancaria.id == data.cuenta_bancaria_id)
    )
    cuenta = cuenta_result.scalars().first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada.")

    extracto = ExtractoBancario(
        company_id=data.company_id,
        cuenta_bancaria_id=data.cuenta_bancaria_id,
        fecha_desde=data.fecha_desde,
        fecha_hasta=data.fecha_hasta,
        saldo_inicial=data.saldo_inicial,
        saldo_final=data.saldo_final,
        total_debitos=data.total_debitos,
        total_creditos=data.total_creditos,
        numero_movimientos=data.numero_movimientos,
        archivo_original=data.archivo_original,
        notas=data.notas,
    )

    db.add(extracto)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="extracto_bancario",
        entity_id=extracto.id,
        description=f"Extracto importado: {cuenta.nombre_banco} ({data.fecha_desde.date()} a {data.fecha_hasta.date()})",
        ip_address=request.client.host if request.client else None,
    )

    resp = ExtractoBancarioResponse.model_validate(extracto)
    resp.banco_nombre = cuenta.nombre_banco
    resp.cuenta_numero = cuenta.numero_cuenta
    return resp


@router.get("/bank/statements", response_model=list[ExtractoBancarioResponse])
async def list_extractos(
    company_id: str | None = None,
    cuenta_bancaria_id: str | None = None,
    estado: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar extractos bancarios"""
    cuenta_bancaria_id = clean_uuid_param(cuenta_bancaria_id, "cuenta_bancaria_id")
    company_id = clean_company_id(company_id)
    query = (
        select(ExtractoBancario)
        .join(Company, ExtractoBancario.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
    )

    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(ExtractoBancario.company_id == company_id)
    if cuenta_bancaria_id:
        query = query.where(ExtractoBancario.cuenta_bancaria_id == cuenta_bancaria_id)
    if estado:
        query = query.where(ExtractoBancario.estado == estado)

    query = query.order_by(ExtractoBancario.created_at.desc())

    result = await db.execute(query)
    extractos = result.scalars().all()

    responses = []
    for ext in extractos:
        resp = ExtractoBancarioResponse.model_validate(ext)
        # Get bank info
        cuenta_result = await db.execute(
            select(CuentaBancaria).where(CuentaBancaria.id == ext.cuenta_bancaria_id)
        )
        cuenta = cuenta_result.scalars().first()
        if cuenta:
            resp.banco_nombre = cuenta.nombre_banco
            resp.cuenta_numero = cuenta.numero_cuenta
        responses.append(resp)

    return responses


@router.get("/bank/statements/{statement_id}", response_model=ExtractoBancarioResponse)
async def get_extracto(
    statement_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un extracto bancario por ID"""
    statement_id = validate_uuid(statement_id, "statement_id")
    result = await db.execute(
        select(ExtractoBancario).where(ExtractoBancario.id == statement_id)
    )
    extracto = result.scalars().first()
    if not extracto:
        raise HTTPException(status_code=404, detail="Extracto no encontrado.")
    await _get_company_for_user(db, extracto.company_id, effective_owner_id(current_user))

    resp = ExtractoBancarioResponse.model_validate(extracto)
    cuenta_result = await db.execute(
        select(CuentaBancaria).where(CuentaBancaria.id == extracto.cuenta_bancaria_id)
    )
    cuenta = cuenta_result.scalars().first()
    if cuenta:
        resp.banco_nombre = cuenta.nombre_banco
        resp.cuenta_numero = cuenta.numero_cuenta
    return resp


@router.delete("/bank/statements/{statement_id}")
async def delete_extracto(
    statement_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un extracto bancario y sus movimientos"""
    statement_id = validate_uuid(statement_id, "statement_id")
    result = await db.execute(
        select(ExtractoBancario).where(ExtractoBancario.id == statement_id)
    )
    extracto = result.scalars().first()
    if not extracto:
        raise HTTPException(status_code=404, detail="Extracto no encontrado.")
    await _get_company_for_user(db, extracto.company_id, effective_owner_id(current_user))

    await db.delete(extracto)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="extracto_bancario",
        entity_id=statement_id,
        description=f"Extracto eliminado",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Extracto eliminado exitosamente."}


# ==========================================
# 4. MOVIMIENTOS BANCARIOS CRUD
# ==========================================

@router.post("/bank/movements", response_model=MovimientoBancarioResponse, status_code=status.HTTP_201_CREATED)
async def create_movimiento(
    data: MovimientoBancarioCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un movimiento bancario"""
    data.cuenta_bancaria_id = clean_uuid_param(data.cuenta_bancaria_id, "cuenta_bancaria_id")
    data.extracto_id = clean_uuid_param(data.extracto_id, "extracto_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # Verify cuenta bancaria ownership
    cuenta_result = await db.execute(
        select(CuentaBancaria).where(CuentaBancaria.id == data.cuenta_bancaria_id)
    )
    cuenta = cuenta_result.scalars().first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada.")

    # Verify extracto exists and belongs to same cuenta
    ext_result = await db.execute(
        select(ExtractoBancario).where(ExtractoBancario.id == data.extracto_id)
    )
    extracto = ext_result.scalars().first()
    if not extracto:
        raise HTTPException(status_code=404, detail="Extracto no encontrado.")
    if extracto.cuenta_bancaria_id != data.cuenta_bancaria_id:
        raise HTTPException(
            status_code=400,
            detail="El extracto no pertenece a la cuenta bancaria indicada.",
        )

    movimiento = MovimientoBancario(
        company_id=data.company_id,
        cuenta_bancaria_id=data.cuenta_bancaria_id,
        extracto_id=data.extracto_id,
        fecha=data.fecha,
        tipo=data.tipo,
        monto=data.monto,
        saldo_posterior=data.saldo_posterior,
        referencia=data.referencia,
        descripcion=data.descripcion,
        beneficiario=data.beneficiario,
        documento=data.documento,
        categoria=data.categoria,
    )

    db.add(movimiento)
    await db.flush()

    # Update cuenta saldo_actual
    if data.tipo == MovimientoTipo.CREDITO.value:
        cuenta.saldo_actual = (cuenta.saldo_actual + data.monto).quantize(Decimal("0.01"))
    else:
        cuenta.saldo_actual = (cuenta.saldo_actual - data.monto).quantize(Decimal("0.01"))
    await db.flush()

    return MovimientoBancarioResponse.model_validate(movimiento)


@router.get("/bank/movements", response_model=list[MovimientoBancarioResponse])
async def list_movimientos(
    extracto_id: str | None = None,
    cuenta_bancaria_id: str | None = None,
    conciliacion_estado: str | None = None,
    tipo: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar movimientos bancarios con filtros"""
    extracto_id = clean_uuid_param(extracto_id, "extracto_id")
    cuenta_bancaria_id = clean_uuid_param(cuenta_bancaria_id, "cuenta_bancaria_id")
    query = (
        select(MovimientoBancario)
        .join(Company, MovimientoBancario.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
    )

    if extracto_id:
        query = query.where(MovimientoBancario.extracto_id == extracto_id)
    if cuenta_bancaria_id:
        query = query.where(MovimientoBancario.cuenta_bancaria_id == cuenta_bancaria_id)
    if conciliacion_estado:
        query = query.where(MovimientoBancario.conciliacion_estado == conciliacion_estado)
    if tipo:
        query = query.where(MovimientoBancario.tipo == tipo)

    query = query.order_by(MovimientoBancario.fecha.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    movimientos = result.scalars().all()
    return [MovimientoBancarioResponse.model_validate(m) for m in movimientos]


@router.put("/bank/movements/{movement_id}", response_model=MovimientoBancarioResponse)
async def update_movimiento(
    movement_id: str,
    data: MovimientoBancarioUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar un movimiento bancario (conciliacion)"""
    movement_id = validate_uuid(movement_id, "movement_id")
    result = await db.execute(
        select(MovimientoBancario).where(MovimientoBancario.id == movement_id)
    )
    movimiento = result.scalars().first()
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado.")
    await _get_company_for_user(db, movimiento.company_id, effective_owner_id(current_user))

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(movimiento, field, value)

    # If conciliacion_estado changed to conciliado, set date
    if "conciliacion_estado" in update_data and update_data["conciliacion_estado"] == ConciliacionEstado.CONCILIADO.value:
        movimiento.conciliacion_fecha = datetime.now(timezone.utc)

    await db.flush()

    # Update extracto conciliados count
    if "conciliacion_estado" in update_data:
        conciliados_count = await db.execute(
            select(func.count(MovimientoBancario.id)).where(
                MovimientoBancario.extracto_id == movimiento.extracto_id,
                MovimientoBancario.conciliacion_estado == ConciliacionEstado.CONCILIADO.value,
            )
        )
        ext_result = await db.execute(
            select(ExtractoBancario).where(ExtractoBancario.id == movimiento.extracto_id)
        )
        ext = ext_result.scalars().first()
        if ext:
            ext.movimientos_conciliados = conciliados_count.scalar() or 0
            # Check if all movements are conciliado or ignorado
            pendientes = await db.execute(
                select(func.count(MovimientoBancario.id)).where(
                    MovimientoBancario.extracto_id == movimiento.extracto_id,
                    MovimientoBancario.conciliacion_estado == ConciliacionEstado.PENDIENTE.value,
                )
            )
            if (pendientes.scalar() or 0) == 0:
                ext.estado = ExtractoEstado.CONCILIADO.value
            else:
                ext.estado = ExtractoEstado.EN_CONCILIACION.value
            await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="movimiento_bancario",
        entity_id=movement_id,
        description=f"Movimiento actualizado: conciliacion={movimiento.conciliacion_estado}",
        ip_address=request.client.host if request.client else None,
    )

    return MovimientoBancarioResponse.model_validate(movimiento)


@router.delete("/bank/movements/{movement_id}")
async def delete_movimiento(
    movement_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un movimiento bancario"""
    movement_id = validate_uuid(movement_id, "movement_id")
    result = await db.execute(
        select(MovimientoBancario).where(MovimientoBancario.id == movement_id)
    )
    movimiento = result.scalars().first()
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado.")
    await _get_company_for_user(db, movimiento.company_id, effective_owner_id(current_user))

    await db.delete(movimiento)
    await db.flush()

    return {"message": "Movimiento eliminado exitosamente."}


# ==========================================
# 5. IMPORTAR EXTRACTO (CSV/Excel parsing)
# ==========================================

def _parse_fecha(value: str) -> date_cls | None:
    """Intenta interpretar una fecha en formatos comunes de extractos bancarios."""
    v = (value or "").strip().strip('"').strip("'")
    if not v:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            continue
    return None


def _parse_monto(value: str) -> Decimal | None:
    """Limpia y convierte un monto (quita $, comas, espacios, parentesis = negativo)."""
    v = (value or "").strip().strip('"').strip("'").replace("$", "").replace(" ", "")
    if not v:
        return None
    negativo = v.startswith("(") and v.endswith(")")
    if negativo:
        v = v[1:-1]
    # Detectar separador decimal por el que aparece al final
    if "," in v and "." in v:
        if v.rfind(",") > v.rfind("."):
            v = v.replace(".", "").replace(",", ".")
        else:
            v = v.replace(",", "")
    elif "," in v:
        partes = v.split(",")
        if len(partes) == 2 and len(partes[1]) in (1, 2):
            v = v.replace(",", ".")
        else:
            v = v.replace(",", "")
    try:
        monto = Decimal(v)
        return -monto if negativo else monto
    except Exception:
        return None


@router.post("/bank/import-csv")
async def import_bank_csv(
    cuenta_bancaria_id: str = Query(...),
    company_id: str = Query(...),
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Importar extracto bancario subiendo el archivo del banco (CSV).
    Detecta las columnas por nombre (fecha, descripcion, debito/credito/monto,
    saldo, referencia) y crea el extracto con sus movimientos.
    """
    company_id = validate_uuid(company_id, "company_id")
    await _get_company_for_user(db, company_id, effective_owner_id(current_user))

    cuenta_result = await db.execute(
        select(CuentaBancaria).where(CuentaBancaria.id == cuenta_bancaria_id)
    )
    cuenta = cuenta_result.scalars().first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta bancaria no encontrada.")

    if file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe adjuntar el archivo de extracto (CSV) para importar los movimientos.",
        )

    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo leer el archivo adjunto.")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de archivo no soportado. Use CSV (UTF-8).")

    try:
        rows = [r for r in csv.reader(io.StringIO(text)) if r and any((c or "").strip() for c in r)]
    except Exception:
        raise HTTPException(status_code=400, detail="El archivo no es un CSV válido.")

    if len(rows) < 2:
        raise HTTPException(
            status_code=400,
            detail="El archivo no contiene movimientos. Verifique que el CSV tenga al menos una fila de datos.",
        )

    # Detectar encabezado: la primera fila es encabezado si alguna columna sugiere un nombre conocido
    header = [str(h).strip().lower() for h in rows[0]]
    KNOWN = ["fecha", "date", "descripcion", "description", "detalle", "monto", "amount",
             "debito", "debit", "credito", "credit", "saldo", "balance", "referencia",
             "reference", "beneficiario", "valor", "importe", "concepto"]
    has_header = any(any(k in h for k in KNOWN) for h in header)
    data_rows = rows[1:] if has_header else rows
    if has_header:
        header = [(h or "") for h in header]
    else:
        header = []

    def find_col(names: list[str]) -> int | None:
        if not header:
            return None
        for i, h in enumerate(header):
            for n in names:
                if n in h:
                    return i
        return None

    col_fecha = find_col(["fecha", "date"])
    col_desc = find_col(["descripcion", "description", "detalle", "concepto", "glosa"])
    col_debito = find_col(["debito", "debit", "debe", "cargo", "retiro", "salida", "egreso", "pago"])
    col_credito = find_col(["credito", "credit", "haber", "abono", "deposito", "ingreso", "entrada"])
    col_monto = find_col(["monto", "amount", "valor", "importe", "total"])
    col_saldo = find_col(["saldo", "balance"])
    col_ref = find_col(["referencia", "reference", "numero", "nro", "num"])
    col_benef = find_col(["beneficiario", "beneficiary", "titular", "originante"])
    col_doc = find_col(["documento", "document", "cheque"])

    movimientos: list[MovimientoBancario] = []
    errores_fila = 0
    fechas: list[date_cls] = []
    total_debitos = Decimal("0")
    total_creditos = Decimal("0")

    for row in data_rows:
        if not row:
            continue
        try:
            # Fecha
            fecha = None
            if col_fecha is not None and col_fecha < len(row):
                fecha = _parse_fecha(row[col_fecha])
            if fecha is None:
                errores_fila += 1
                continue
            fechas.append(fecha)

            # Tipo y monto
            monto = None
            tipo = None
            if col_debito is not None and col_debito < len(row) and _parse_monto(row[col_debito]) not in (None, Decimal("0")):
                monto = _parse_monto(row[col_debito])
                tipo = MovimientoTipo.DEBITO.value
            elif col_credito is not None and col_credito < len(row) and _parse_monto(row[col_credito]) not in (None, Decimal("0")):
                monto = _parse_monto(row[col_credito])
                tipo = MovimientoTipo.CREDITO.value
            elif col_monto is not None and col_monto < len(row):
                monto = _parse_monto(row[col_monto])
                if monto is None:
                    errores_fila += 1
                    continue
                tipo = MovimientoTipo.DEBITO.value if monto < 0 else MovimientoTipo.CREDITO.value
                monto = abs(monto)
            else:
                errores_fila += 1
                continue

            if monto is None or monto <= 0:
                errores_fila += 1
                continue

            desc = ""
            if col_desc is not None and col_desc < len(row):
                desc = (row[col_desc] or "").strip()
            ref = None
            if col_ref is not None and col_ref < len(row):
                ref = (row[col_ref] or "").strip()[:100] or None
            benef = None
            if col_benef is not None and col_benef < len(row):
                benef = (row[col_benef] or "").strip()[:200] or None
            doc = None
            if col_doc is not None and col_doc < len(row):
                doc = (row[col_doc] or "").strip()[:50] or None
            saldo = None
            if col_saldo is not None and col_saldo < len(row):
                saldo = _parse_monto(row[col_saldo])

            if tipo == MovimientoTipo.DEBITO.value:
                total_debitos += monto
            else:
                total_creditos += monto

            movimientos.append(MovimientoBancario(
                company_id=company_id,
                cuenta_bancaria_id=cuenta_bancaria_id,
                fecha=datetime.combine(fecha, datetime.min.time(), tzinfo=timezone.utc),
                tipo=tipo,
                monto=monto,
                saldo_posterior=saldo,
                referencia=ref,
                descripcion=desc or None,
                beneficiario=benef,
                documento=doc,
                conciliacion_estado=ConciliacionEstado.PENDIENTE.value,
            ))
        except Exception:
            errores_fila += 1
            continue

    if not movimientos:
        raise HTTPException(
            status_code=400,
            detail="No se pudieron extraer movimientos del archivo. Verifique el formato de las columnas (fecha, monto/debito/credito).",
        )

    extracto = ExtractoBancario(
        company_id=company_id,
        cuenta_bancaria_id=cuenta_bancaria_id,
        fecha_desde=datetime.combine(min(fechas), datetime.min.time(), tzinfo=timezone.utc),
        fecha_hasta=datetime.combine(max(fechas), datetime.min.time(), tzinfo=timezone.utc),
        saldo_inicial=Decimal("0"),
        saldo_final=total_creditos - total_debitos,
        total_debitos=total_debitos,
        total_creditos=total_creditos,
        estado=ExtractoEstado.IMPORTADO.value,
        numero_movimientos=len(movimientos),
        archivo_original=(file.filename or "extracto.csv")[:500],
    )
    extracto.movimientos = movimientos
    db.add(extracto)
    await db.flush()

    # Update last sync date
    cuenta.ultima_fecha_sincronizacion = datetime.now(timezone.utc)
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="IMPORT", entity_type="extracto_bancario", entity_id=extracto.id,
        description=f"Extracto importado desde archivo: {len(movimientos)} movimientos ({file.filename})",
        ip_address=request.client.host if request.client else None,
    )

    return {
        "message": f"Extracto importado exitosamente: {len(movimientos)} movimientos procesados.",
        "cuenta_id": cuenta_bancaria_id,
        "extracto_id": extracto.id,
        "movimientos_importados": len(movimientos),
        "filas_ignoradas": errores_fila,
    }


# ==========================================
# 6. E-COMMERCE CONNECTORS CRUD
# ==========================================

@router.post("/ecommerce/connectors", response_model=EcommerceConnectorResponse, status_code=status.HTTP_201_CREATED)
async def create_ecommerce_connector(
    data: EcommerceConnectorCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un conector e-commerce"""
    data.company_id = validate_uuid(data.company_id, "company_id")
    try:
        await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))
    except HTTPException:
        raise

    # Validate plataforma
    valid_plataformas = {p.value for p in EcommercePlataforma}
    if data.plataforma not in valid_plataformas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plataforma invalida: {data.plataforma}",
        )

    try:
        connector = EcommerceConnector(
            company_id=data.company_id,
            user_id=current_user.id,
            nombre=data.nombre,
            plataforma=data.plataforma,
            url_tienda=data.url_tienda,
            api_key=data.api_key,
            api_secret=data.api_secret,
            access_token=data.access_token,
            refresh_token=data.refresh_token,
            configuracion_extra=data.configuracion_extra,
            sincronizacion_auto=data.sincronizacion_auto,
            frecuencia_sync=data.frecuencia_sync,
            sync_productos=data.sync_productos,
            sync_ordenes=data.sync_ordenes,
            sync_clientes=data.sync_clientes,
            sync_inventario=data.sync_inventario,
        )

        db.add(connector)
        await db.flush()

        await log_action(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            action="CREATE",
            entity_type="ecommerce_connector",
            entity_id=connector.id,
            description=f"Conector e-commerce creado: {connector.nombre} ({connector.plataforma})",
            ip_address=request.client.host if request.client else None,
        )

        return EcommerceConnectorResponse.model_validate(connector)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating e-commerce connector: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear conector e-commerce: {str(e)}",
        )


@router.get("/ecommerce/connectors", response_model=list[EcommerceConnectorResponse])
async def list_ecommerce_connectors(
    company_id: str | None = None,
    plataforma: str | None = None,
    is_active: bool | None = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar conectores e-commerce"""
    company_id = clean_company_id(company_id)
    try:
        query = (
            select(EcommerceConnector)
            .options(selectinload(EcommerceConnector.sincronizaciones))
            .join(Company, EcommerceConnector.company_id == Company.id)
            .where(Company.user_id == effective_owner_id(current_user))
        )

        if company_id:
            await _get_company_for_user(db, company_id, effective_owner_id(current_user))
            query = query.where(EcommerceConnector.company_id == company_id)
        if plataforma:
            query = query.where(EcommerceConnector.plataforma == plataforma)
        if is_active is not None:
            query = query.where(EcommerceConnector.is_active == is_active)

        query = query.order_by(EcommerceConnector.created_at.desc())

        result = await db.execute(query)
        connectors = result.scalars().all()
        return [EcommerceConnectorResponse.model_validate(c) for c in connectors]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing e-commerce connectors: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar conectores e-commerce: {str(e)}",
        )


@router.get("/ecommerce/connectors/{connector_id}", response_model=EcommerceConnectorResponse)
async def get_ecommerce_connector(
    connector_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un conector e-commerce por ID"""
    connector_id = validate_uuid(connector_id, "connector_id")
    result = await db.execute(
        select(EcommerceConnector).where(EcommerceConnector.id == connector_id)
    )
    connector = result.scalars().first()
    if not connector:
        raise HTTPException(status_code=404, detail="Conector no encontrado.")
    await _get_company_for_user(db, connector.company_id, effective_owner_id(current_user))
    return EcommerceConnectorResponse.model_validate(connector)


@router.put("/ecommerce/connectors/{connector_id}", response_model=EcommerceConnectorResponse)
async def update_ecommerce_connector(
    connector_id: str,
    data: EcommerceConnectorUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar un conector e-commerce"""
    connector_id = validate_uuid(connector_id, "connector_id")
    result = await db.execute(
        select(EcommerceConnector).where(EcommerceConnector.id == connector_id)
    )
    connector = result.scalars().first()
    if not connector:
        raise HTTPException(status_code=404, detail="Conector no encontrado.")
    await _get_company_for_user(db, connector.company_id, effective_owner_id(current_user))

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(connector, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="ecommerce_connector",
        entity_id=connector.id,
        description=f"Conector actualizado: {connector.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return EcommerceConnectorResponse.model_validate(connector)


@router.delete("/ecommerce/connectors/{connector_id}")
async def delete_ecommerce_connector(
    connector_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un conector e-commerce"""
    connector_id = validate_uuid(connector_id, "connector_id")
    result = await db.execute(
        select(EcommerceConnector).where(EcommerceConnector.id == connector_id)
    )
    connector = result.scalars().first()
    if not connector:
        raise HTTPException(status_code=404, detail="Conector no encontrado.")
    await _get_company_for_user(db, connector.company_id, effective_owner_id(current_user))

    connector.is_active = False
    connector.estado = ConnectorEstado.DESACTIVADO.value
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="ecommerce_connector",
        entity_id=connector_id,
        description=f"Conector desactivado: {connector.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Conector desactivado exitosamente."}


# ==========================================
# 7. PROBAR CONEXION E-COMMERCE
# ==========================================

@router.post("/ecommerce/connectors/{connector_id}/test")
async def test_ecommerce_connection(
    connector_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Probar la conexion con la plataforma e-commerce"""
    connector_id = validate_uuid(connector_id, "connector_id")
    result = await db.execute(
        select(EcommerceConnector).where(EcommerceConnector.id == connector_id)
    )
    connector = result.scalars().first()
    if not connector:
        raise HTTPException(status_code=404, detail="Conector no encontrado.")
    await _get_company_for_user(db, connector.company_id, effective_owner_id(current_user))

    # In production, this would make actual API calls to the platform
    # For now, simulate a connection test
    try:
        # Simulate API test based on platform
        if connector.api_key or connector.access_token:
            connector.estado = ConnectorEstado.CONECTADO.value
            connector.ultimo_error = None
        else:
            connector.estado = ConnectorEstado.ERROR.value
            connector.ultimo_error = "No se encontraron credenciales de API configuradas."

        await db.flush()

        await log_action(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            action="TEST",
            entity_type="ecommerce_connector",
            entity_id=connector.id,
            description=f"Test conexion {connector.plataforma}: {connector.estado}",
            ip_address=request.client.host if request.client else None,
        )

        return {
            "status": connector.estado,
            "message": (
                "Conexion exitosa." if connector.estado == ConnectorEstado.CONECTADO.value
                else f"Error de conexion: {connector.ultimo_error}"
            ),
        }
    except Exception as e:
        connector.estado = ConnectorEstado.ERROR.value
        connector.ultimo_error = str(e)
        await db.flush()
        raise HTTPException(
            status_code=400,
            detail=f"Error al probar conexion: {str(e)}",
        )


# ==========================================
# 8. SINCRONIZACION E-COMMERCE
# ==========================================

@router.post("/ecommerce/connectors/{connector_id}/sync", response_model=EcommerceSyncLogResponse)
async def sync_ecommerce(
    connector_id: str,
    request: Request,
    tipo_sync: str = Query("completo", pattern="^(productos|ordenes|clientes|inventario|completo)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ejecutar sincronizacion con la plataforma e-commerce"""
    connector_id = validate_uuid(connector_id, "connector_id")
    result = await db.execute(
        select(EcommerceConnector).where(EcommerceConnector.id == connector_id)
    )
    connector = result.scalars().first()
    if not connector:
        raise HTTPException(status_code=404, detail="Conector no encontrado.")
    await _get_company_for_user(db, connector.company_id, effective_owner_id(current_user))

    if connector.estado not in [ConnectorEstado.CONECTADO.value, ConnectorEstado.SINCRONIZANDO.value]:
        raise HTTPException(
            status_code=400,
            detail="El conector debe estar conectado antes de sincronizar. Pruebe la conexion primero.",
        )

    # Create sync log
    sync_log = EcommerceSyncLog(
        company_id=connector.company_id,
        connector_id=connector_id,
        tipo_sync=tipo_sync,
        estado=SyncEstado.EN_PROGRESO.value,
        creado_por=current_user.id,
    )

    # Update connector state
    connector.estado = ConnectorEstado.SINCRONIZANDO.value
    db.add(sync_log)
    await db.flush()

    # In production, this would call the actual e-commerce API
    # Simulate a successful sync
    sync_log.estado = SyncEstado.COMPLETADA.value
    sync_log.fecha_fin = datetime.now(timezone.utc)
    sync_log.registros_procesados = 0
    sync_log.registros_creados = 0
    sync_log.registros_actualizados = 0
    sync_log.registros_errores = 0
    sync_log.resultado_resumen = '{"message": "Sincronizacion completada. No hay datos nuevos para sincronizar."}'

    connector.estado = ConnectorEstado.CONECTADO.value
    connector.ultima_sincronizacion = datetime.now(timezone.utc)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="SYNC",
        entity_type="ecommerce_connector",
        entity_id=connector.id,
        description=f"Sincronizacion {tipo_sync} en {connector.plataforma}: completada",
        ip_address=request.client.host if request.client else None,
    )

    resp = EcommerceSyncLogResponse.model_validate(sync_log)
    resp.connector_nombre = connector.nombre
    resp.connector_plataforma = connector.plataforma
    return resp


# ==========================================
# 9. SYNC LOGS
# ==========================================

@router.get("/ecommerce/sync-logs", response_model=list[EcommerceSyncLogResponse])
async def list_sync_logs(
    connector_id: str | None = None,
    company_id: str | None = None,
    tipo_sync: str | None = None,
    estado: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar logs de sincronizacion e-commerce"""
    connector_id = clean_uuid_param(connector_id, "connector_id")
    company_id = clean_company_id(company_id)
    query = (
        select(EcommerceSyncLog)
        .join(Company, EcommerceSyncLog.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
    )

    if connector_id:
        query = query.where(EcommerceSyncLog.connector_id == connector_id)
    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(EcommerceSyncLog.company_id == company_id)
    if tipo_sync:
        query = query.where(EcommerceSyncLog.tipo_sync == tipo_sync)
    if estado:
        query = query.where(EcommerceSyncLog.estado == estado)

    query = query.order_by(EcommerceSyncLog.fecha_inicio.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    responses = []
    for log in logs:
        resp = EcommerceSyncLogResponse.model_validate(log)
        # Get connector info
        conn_result = await db.execute(
            select(EcommerceConnector).where(EcommerceConnector.id == log.connector_id)
        )
        conn = conn_result.scalars().first()
        if conn:
            resp.connector_nombre = conn.nombre
            resp.connector_plataforma = conn.plataforma
        responses.append(resp)

    return responses


# ==========================================
# Feature 2: E-Commerce Connectors (Fase 15)
# ==========================================

async def _get_connector_for_user(
    db: AsyncSession,
    connector_id: str,
    user_id: str,
) -> EcommerceConnector:
    """Get a connector verifying ownership by user"""
    result = await db.execute(
        select(EcommerceConnector)
        .join(Company, EcommerceConnector.company_id == Company.id)
        .where(
            EcommerceConnector.id == connector_id,
            Company.user_id == user_id,
        )
    )
    connector = result.scalars().first()
    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conector no encontrado o no pertenece al usuario.",
        )
    return connector


async def _fetch_woocommerce_products(connector: EcommerceConnector) -> list[dict]:
    """Fetch products from WooCommerce REST API"""
    import aiohttp
    import base64

    auth = base64.b64encode(f"{connector.api_key}:{connector.api_secret}".encode()).decode()
    url = f"{connector.url_tienda.rstrip('/')}/wp-json/wc/v3/products"
    params = {"per_page": 100, "status": "publish"}

    products = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"Authorization": f"Basic {auth}"},
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    products = await resp.json()
                else:
                    logger.error(f"WooCommerce products fetch failed: {resp.status}")
    except Exception as e:
        logger.error(f"Error fetching WooCommerce products: {e}")
        raise
    return products


async def _fetch_shopify_products(connector: EcommerceConnector) -> list[dict]:
    """Fetch products from Shopify REST API"""
    import aiohttp

    url = f"{connector.url_tienda.rstrip('/')}/admin/api/2024-01/products.json"
    params = {"limit": 250}
    headers = {"X-Shopify-Access-Token": connector.access_token or ""}

    products = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    products = data.get("products", [])
                else:
                    logger.error(f"Shopify products fetch failed: {resp.status}")
    except Exception as e:
        logger.error(f"Error fetching Shopify products: {e}")
        raise
    return products


async def _fetch_woocommerce_orders(connector: EcommerceConnector) -> list[dict]:
    """Fetch orders from WooCommerce REST API"""
    import aiohttp
    import base64

    auth = base64.b64encode(f"{connector.api_key}:{connector.api_secret}".encode()).decode()
    url = f"{connector.url_tienda.rstrip('/')}/wp-json/wc/v3/orders"
    after_date = datetime.now(timezone.utc).replace(day=1).isoformat()
    params = {"per_page": 100, "status": "processing,completed", "after": after_date}

    orders = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                params=params,
                headers={"Authorization": f"Basic {auth}"},
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    orders = await resp.json()
                else:
                    logger.error(f"WooCommerce orders fetch failed: {resp.status}")
    except Exception as e:
        logger.error(f"Error fetching WooCommerce orders: {e}")
        raise
    return orders


async def _fetch_shopify_orders(connector: EcommerceConnector) -> list[dict]:
    """Fetch orders from Shopify REST API"""
    import aiohttp

    url = f"{connector.url_tienda.rstrip('/')}/admin/api/2024-01/orders.json"
    params = {"status": "open", "limit": 250}
    headers = {"X-Shopify-Access-Token": connector.access_token or ""}

    orders = []
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    orders = data.get("orders", [])
                else:
                    logger.error(f"Shopify orders fetch failed: {resp.status}")
    except Exception as e:
        logger.error(f"Error fetching Shopify orders: {e}")
        raise
    return orders


async def _push_woocommerce_inventory(connector: EcommerceConnector, sku: str, stock: int) -> bool:
    """Push stock level to WooCommerce"""
    import aiohttp
    import base64

    auth = base64.b64encode(f"{connector.api_key}:{connector.api_secret}".encode()).decode()
    search_url = f"{connector.url_tienda.rstrip('/')}/wp-json/wc/v3/products"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                search_url,
                params={"sku": sku, "per_page": 1},
                headers={"Authorization": f"Basic {auth}"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    products = await resp.json()
                    if products:
                        product_id = products[0]["id"]
                        update_url = f"{connector.url_tienda.rstrip('/')}/wp-json/wc/v3/products/{product_id}"
                        async with session.put(
                            update_url,
                            json={"stock_quantity": stock, "manage_stock": True},
                            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
                            timeout=aiohttp.ClientTimeout(total=30),
                        ) as update_resp:
                            return update_resp.status in (200, 201)
    except Exception as e:
        logger.error(f"Error pushing to WooCommerce inventory: {e}")
    return False


async def _push_shopify_inventory(connector: EcommerceConnector, product_id: str, variant_id: str, stock: int) -> bool:
    """Push stock level to Shopify"""
    import aiohttp

    url = f"{connector.url_tienda.rstrip('/')}/admin/api/2024-01/variants/{variant_id}.json"
    headers = {
        "X-Shopify-Access-Token": connector.access_token or "",
        "Content-Type": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(
                url,
                json={"variant": {"id": variant_id, "inventory_quantity": stock}},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                return resp.status in (200, 201)
    except Exception as e:
        logger.error(f"Error pushing to Shopify inventory: {e}")
    return False


@router.post("/ecommerce/{connector_id}/sync-products", response_model=EcommerceSyncProductsResponse)
async def sync_ecommerce_products(
    connector_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync products from e-commerce platform to ContaEC.
    Maps: e-commerce product -> ContaEC Product
    (sku->codigo_principal, title->descripcion, price->precio_venta, stock->stock_actual)
    Supports: woocommerce, shopify
    """
    connector_id = validate_uuid(connector_id, "connector_id")
    from app.models.product import Product, ProductoTipo

    connector = await _get_connector_for_user(db, connector_id, current_user.id)

    if connector.estado not in [ConnectorEstado.CONECTADO.value, ConnectorEstado.CONFIGURADO.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El conector debe estar conectado o configurado para sincronizar productos.",
        )

    if not connector.sync_productos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La sincronizacion de productos esta deshabilitada para este conector.",
        )

    sync_log = EcommerceSyncLog(
        company_id=connector.company_id,
        connector_id=connector_id,
        tipo_sync="productos",
        estado=SyncEstado.EN_PROGRESO.value,
        creado_por=current_user.id,
    )
    db.add(sync_log)
    await db.flush()

    try:
        if connector.plataforma == EcommercePlataforma.WOOCOMMERCE.value:
            external_products = await _fetch_woocommerce_products(connector)
        elif connector.plataforma == EcommercePlataforma.SHOPFIY.value:
            external_products = await _fetch_shopify_products(connector)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plataforma no soportada para sincronizacion de productos: {connector.plataforma}",
            )
    except HTTPException:
        raise
    except Exception as e:
        sync_log.estado = SyncEstado.CON_ERROR.value
        sync_log.fecha_fin = datetime.now(timezone.utc)
        sync_log.detalle_errores = str(e)
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al obtener productos de la plataforma: {str(e)}",
        )

    processed = 0
    created = 0
    updated = 0
    errors: list[str] = []

    for ep in external_products:
        processed += 1
        try:
            if connector.plataforma == EcommercePlataforma.WOOCOMMERCE.value:
                sku = ep.get("sku") or f"WC-{ep.get('id')}"
                descripcion = ep.get("name", "Sin nombre")
                precio = float(ep.get("regular_price") or ep.get("price") or 0)
                stock_val = ep.get("stock_quantity") or 0
            else:
                sku = ep.get("variants", [{}])[0].get("sku") or f"SH-{ep.get('id')}"
                descripcion = ep.get("title", "Sin nombre")
                precio = float(ep.get("variants", [{}])[0].get("price") or 0)
                stock_val = ep.get("variants", [{}])[0].get("inventory_quantity") or 0

            existing_result = await db.execute(
                select(Product).where(
                    Product.company_id == connector.company_id,
                    Product.codigo_principal == sku,
                )
            )
            existing = existing_result.scalars().first()

            if existing:
                existing.descripcion = descripcion
                existing.precio_unitario = Decimal(str(precio))
                existing.stock = Decimal(str(stock_val))
                existing.updated_at = datetime.now(timezone.utc)
                updated += 1
            else:
                product = Product(
                    company_id=connector.company_id,
                    codigo_principal=sku,
                    descripcion=descripcion,
                    tipo=ProductoTipo.BIEN.value,
                    precio_unitario=Decimal(str(precio)),
                    iva_codigo="10",
                    iva_porcentaje=Decimal("12"),
                    unidad_medida="Unidad",
                    stock=Decimal(str(stock_val)),
                    stock_minimo=Decimal("0"),
                )
                db.add(product)
                created += 1

        except Exception as e:
            errors.append(f"Error processing product {ep.get('id', 'unknown')}: {str(e)}")

    sync_log.estado = SyncEstado.COMPLETADA.value
    sync_log.fecha_fin = datetime.now(timezone.utc)
    sync_log.registros_procesados = processed
    sync_log.registros_creados = created
    sync_log.registros_actualizados = updated
    sync_log.registros_errores = len(errors)
    if errors:
        sync_log.detalle_errores = "\n".join(errors[:50])

    connector.total_productos_sync += created
    connector.ultima_sincronizacion = datetime.now(timezone.utc)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="ECOMMERCE_SYNC_PRODUCTS",
        entity_type="ecommerce_connector",
        entity_id=connector.id,
        description=f"Sincronizacion de productos desde {connector.plataforma}: {created} creados, {updated} actualizados",
        ip_address=request.client.host if request.client else None,
    )

    return EcommerceSyncProductsResponse(
        connector_id=connector_id,
        connector_nombre=connector.nombre,
        plataforma=connector.plataforma,
        total_procesados=processed,
        total_creados=created,
        total_actualizados=updated,
        total_errores=len(errors),
        errores=errors[:10],
        sync_log_id=sync_log.id,
    )


@router.post("/ecommerce/{connector_id}/sync-orders", response_model=EcommerceSyncOrdersResponse)
async def sync_ecommerce_orders(
    connector_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync orders from e-commerce platform to ContaEC.
    Creates Factura (Comprobante) in ContaEC from each e-commerce order.
    Maps: order->comprobante, customer->cliente, items->detalles
    """
    connector_id = validate_uuid(connector_id, "connector_id")
    from app.models.comprobante import Comprobante, ComprobanteDetalle, ComprobanteEstado, ComprobanteTipo
    from app.models.client import Client

    connector = await _get_connector_for_user(db, connector_id, current_user.id)

    if connector.estado not in [ConnectorEstado.CONECTADO.value, ConnectorEstado.CONFIGURADO.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El conector debe estar conectado o configurado para sincronizar ordenes.",
        )

    if not connector.sync_ordenes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La sincronizacion de ordenes esta deshabilitada para este conector.",
        )

    sync_log = EcommerceSyncLog(
        company_id=connector.company_id,
        connector_id=connector_id,
        tipo_sync="ordenes",
        estado=SyncEstado.EN_PROGRESO.value,
        creado_por=current_user.id,
    )
    db.add(sync_log)
    await db.flush()

    try:
        if connector.plataforma == EcommercePlataforma.WOOCOMMERCE.value:
            external_orders = await _fetch_woocommerce_orders(connector)
        elif connector.plataforma == EcommercePlataforma.SHOPFIY.value:
            external_orders = await _fetch_shopify_orders(connector)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plataforma no soportada para sincronizacion de ordenes: {connector.plataforma}",
            )
    except HTTPException:
        raise
    except Exception as e:
        sync_log.estado = SyncEstado.CON_ERROR.value
        sync_log.fecha_fin = datetime.now(timezone.utc)
        sync_log.detalle_errores = str(e)
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al obtener ordenes de la plataforma: {str(e)}",
        )

    processed = 0
    facturas_creadas = 0
    errors: list[str] = []

    for order in external_orders:
        processed += 1
        try:
            ext_order_id = str(order.get("id", ""))
            existing_result = await db.execute(
                select(Comprobante).where(
                    Comprobante.company_id == connector.company_id,
                    Comprobante.referencia_id == ext_order_id,
                    Comprobante.referencia_tipo == "ecommerce_order",
                )
            )
            if existing_result.scalars().first():
                continue

            if connector.plataforma == EcommercePlataforma.WOOCOMMERCE.value:
                billing = order.get("billing", {})
                customer_email = billing.get("email", "")
                customer_name = f"{billing.get('first_name', '')} {billing.get('last_name', '')}".strip()
                customer_id_doc = billing.get("cpf") or billing.get("cuit") or ""
                order_total = float(order.get("total") or 0)
                line_items = order.get("line_items", [])
                order_date_str = order.get("date_created", "")
            else:
                billing = order.get("billing_address", {})
                customer_email = order.get("email", "")
                customer_name = f"{order.get('customer', {}).get('first_name', '')} {order.get('customer', {}).get('last_name', '')}".strip()
                customer_id_doc = ""
                order_total = float(order.get("total_price") or 0)
                line_items = order.get("line_items", [])
                order_date_str = order.get("created_at", "")

            order_date = datetime.now(timezone.utc)
            if order_date_str:
                try:
                    order_date = datetime.fromisoformat(order_date_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            client_result = await db.execute(
                select(Client).where(
                    Client.company_id == connector.company_id,
                    Client.email == customer_email,
                )
            )
            client = client_result.scalars().first()
            if not client and customer_name:
                client = Client(
                    company_id=connector.company_id,
                    nombre=customer_name,
                    email=customer_email or None,
                    identificacion=customer_id_doc or None,
                    tipo_cliente="consumidor_final",
                )
                db.add(client)
                await db.flush()

            secuencial_result = await db.execute(
                select(func.coalesce(func.max(func.cast(Comprobante.secuencial, Integer)), 0)).where(
                    Comprobante.company_id == connector.company_id,
                    Comprobante.tipo_comprobante == ComprobanteTipo.FACTURA.value,
                )
            )
            next_sec = (secuencial_result.scalar() or 0) + 1
            secuencial = f"{next_sec:09d}"

            subtotal = Decimal(str(order_total)) / Decimal("1.12")
            iva = Decimal(str(order_total)) - subtotal

            comprobante = Comprobante(
                company_id=connector.company_id,
                client_id=client.id if client else None,
                user_id=current_user.id,
                tipo_comprobante=ComprobanteTipo.FACTURA.value,
                secuencial=secuencial,
                fecha_emision=order_date,
                estado=ComprobanteEstado.AUTORIZADO.value,
                ambiente="1",
                subtotal_sin_iva=subtotal.quantize(Decimal("0.01")),
                subtotal_con_iva=Decimal(str(order_total)).quantize(Decimal("0.01")),
                subtotal_iva=iva.quantize(Decimal("0.01")),
                iva_porcentaje=Decimal("12"),
                total=Decimal(str(order_total)).quantize(Decimal("0.01")),
                referencia_tipo="ecommerce_order",
                referencia_id=ext_order_id,
                referencia_secuencial=order.get("number") or order.get("name") or ext_order_id,
                cliente_nombre=customer_name or "Cliente E-Commerce",
                cliente_email=customer_email or "",
                cliente_identificacion=customer_id_doc or "9999999999",
            )

            for item in line_items:
                item_name = item.get("name", "Producto")
                item_qty = item.get("quantity") or 1
                item_price = float(item.get("price") or item.get("total") or 0)
                item_subtotal = Decimal(str(item_price))

                detalle = ComprobanteDetalle(
                    codigo_principal=item.get("sku") or item.get("product_id") or "",
                    descripcion=item_name,
                    cantidad=Decimal(str(item_qty)),
                    precio_unitario=item_subtotal,
                    subtotal=item_subtotal.quantize(Decimal("0.01")),
                    iva_porcentaje=Decimal("12"),
                )
                comprobante.detalles.append(detalle)

            db.add(comprobante)
            facturas_creadas += 1

        except Exception as e:
            errors.append(f"Error processing order {order.get('id', 'unknown')}: {str(e)}")

    sync_log.estado = SyncEstado.COMPLETADA.value
    sync_log.fecha_fin = datetime.now(timezone.utc)
    sync_log.registros_procesados = processed
    sync_log.registros_creados = facturas_creadas
    sync_log.registros_errores = len(errors)
    if errors:
        sync_log.detalle_errores = "\n".join(errors[:50])

    connector.total_ordenes_sync += facturas_creadas
    connector.ultima_sincronizacion = datetime.now(timezone.utc)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="ECOMMERCE_SYNC_ORDERS",
        entity_type="ecommerce_connector",
        entity_id=connector.id,
        description=f"Sincronizacion de ordenes desde {connector.plataforma}: {facturas_creadas} facturas creadas",
        ip_address=request.client.host if request.client else None,
    )

    return EcommerceSyncOrdersResponse(
        connector_id=connector_id,
        connector_nombre=connector.nombre,
        plataforma=connector.plataforma,
        total_ordenes_procesadas=processed,
        total_facturas_creadas=facturas_creadas,
        total_errores=len(errors),
        errores=errors[:10],
        sync_log_id=sync_log.id,
    )


@router.post("/ecommerce/{connector_id}/sync-inventory", response_model=EcommerceSyncInventoryResponse)
async def sync_ecommerce_inventory(
    connector_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync inventory from ContaEC to e-commerce platform.
    Pushes stock levels back to e-commerce platform.
    """
    connector_id = validate_uuid(connector_id, "connector_id")
    from app.models.product import Product

    connector = await _get_connector_for_user(db, connector_id, current_user.id)

    if connector.estado not in [ConnectorEstado.CONECTADO.value, ConnectorEstado.CONFIGURADO.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El conector debe estar conectado o configurado para sincronizar inventario.",
        )

    if not connector.sync_inventario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La sincronizacion de inventario esta deshabilitada para este conector.",
        )

    sync_log = EcommerceSyncLog(
        company_id=connector.company_id,
        connector_id=connector_id,
        tipo_sync="inventario",
        estado=SyncEstado.EN_PROGRESO.value,
        creado_por=current_user.id,
    )
    db.add(sync_log)
    await db.flush()

    products_result = await db.execute(
        select(Product).where(
            Product.company_id == connector.company_id,
            Product.is_active == True,
        )
    )
    products = products_result.scalars().all()

    processed = 0
    stock_updated = 0
    errors: list[str] = []

    for product in products:
        processed += 1
        try:
            stock = int(product.stock)

            if connector.plataforma == EcommercePlataforma.WOOCOMMERCE.value:
                success = await _push_woocommerce_inventory(connector, product.codigo_principal, stock)
                if success:
                    stock_updated += 1
            elif connector.plataforma == EcommercePlataforma.SHOPFIY.value:
                import json
                config = {}
                if connector.configuracion_extra:
                    try:
                        config = json.loads(connector.configuracion_extra)
                    except json.JSONDecodeError:
                        pass

                product_id = config.get("product_ids", {}).get(product.codigo_principal, "")
                variant_id = config.get("variant_ids", {}).get(product.codigo_principal, "")

                if variant_id:
                    success = await _push_shopify_inventory(connector, product_id, variant_id, stock)
                    if success:
                        stock_updated += 1
                else:
                    errors.append(f"No variant_id mapped for product {product.codigo_principal}")
            else:
                errors.append(f"Plataforma no soportada: {connector.plataforma}")

        except Exception as e:
            errors.append(f"Error syncing inventory for {product.codigo_principal}: {str(e)}")

    sync_log.estado = SyncEstado.COMPLETADA.value
    sync_log.fecha_fin = datetime.now(timezone.utc)
    sync_log.registros_procesados = processed
    sync_log.registros_actualizados = stock_updated
    sync_log.registros_errores = len(errors)
    if errors:
        sync_log.detalle_errores = "\n".join(errors[:50])

    connector.ultima_sincronizacion = datetime.now(timezone.utc)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="ECOMMERCE_SYNC_INVENTORY",
        entity_type="ecommerce_connector",
        entity_id=connector.id,
        description=f"Sincronizacion de inventario hacia {connector.plataforma}: {stock_updated} productos actualizados",
        ip_address=request.client.host if request.client else None,
    )

    return EcommerceSyncInventoryResponse(
        connector_id=connector_id,
        connector_nombre=connector.nombre,
        plataforma=connector.plataforma,
        total_productos_procesados=processed,
        total_stock_actualizados=stock_updated,
        total_errores=len(errors),
        errores=errors[:10],
        sync_log_id=sync_log.id,
    )


@router.get("/ecommerce/{connector_id}/status", response_model=EcommerceConnectorStatus)
async def get_ecommerce_connector_status(
    connector_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get last sync status, errors, and product count for an e-commerce connector.
    """
    connector_id = validate_uuid(connector_id, "connector_id")
    connector = await _get_connector_for_user(db, connector_id, current_user.id)

    last_sync_result = await db.execute(
        select(EcommerceSyncLog)
        .where(EcommerceSyncLog.connector_id == connector_id)
        .order_by(EcommerceSyncLog.fecha_inicio.desc())
        .limit(1)
    )
    last_sync = last_sync_result.scalars().first()

    last_sync_details = None
    if last_sync:
        last_sync_details = {
            "tipo_sync": last_sync.tipo_sync,
            "estado": last_sync.estado,
            "fecha_inicio": last_sync.fecha_inicio.isoformat() if last_sync.fecha_inicio else None,
            "fecha_fin": last_sync.fecha_fin.isoformat() if last_sync.fecha_fin else None,
            "registros_procesados": last_sync.registros_procesados,
            "registros_creados": last_sync.registros_creados,
            "registros_actualizados": last_sync.registros_actualizados,
            "registros_errores": last_sync.registros_errores,
            "ultimo_error": last_sync.detalle_errores[:200] if last_sync.detalle_errores else None,
        }

    return EcommerceConnectorStatus(
        connector_id=connector_id,
        connector_nombre=connector.nombre,
        plataforma=connector.plataforma,
        estado=connector.estado,
        url_tienda=connector.url_tienda,
        ultima_sincronizacion=connector.ultima_sincronizacion,
        ultimo_error=connector.ultimo_error,
        total_productos_sync=connector.total_productos_sync,
        total_ordenes_sync=connector.total_ordenes_sync,
        is_active=connector.is_active,
        sync_productos=connector.sync_productos,
        sync_ordenes=connector.sync_ordenes,
        sync_inventario=connector.sync_inventario,
        sync_clientes=connector.sync_clientes,
        ultima_sync_details=last_sync_details,
    )

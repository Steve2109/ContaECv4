"""
ContaEC - API Endpoints de Contabilidad Core
Plan de Cuentas, Asientos Contables, Cuentas por Cobrar, Pagos, Períodos Fiscales
"""
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.accounting import (
    AsientoContable,
    AsientoDetalle,
    AsientoEstado,
    CuentaContable,
    CuentaPorCobrar,
    CuentaPorCobrarEstado,
    NaturalezaCuenta,
    Pago,
    PagoEstado,
    PagoTipo,
    PeriodoFiscal,
    PeriodoFiscalEstado,
    TipoAsiento,
    TipoCuentaContable,
)
from app.models.comprobante import Comprobante, ComprobanteEstado
from app.models.purchase import CuentaPorPagar
from app.models.user import User
from app.schemas.accounting import (
    AsientoContableCreate,
    AsientoContableResponse,
    AsientoContableUpdate,
    AsientoDetalleResponse,
    BalanceComprobacionItem,
    BalanceComprobacionResponse,
    ContabilidadStats,
    CuentaContableCreate,
    CuentaContableResponse,
    CuentaContableUpdate,
    CuentaPorCobrarCreate,
    CuentaPorCobrarResponse,
    CuentaPorCobrarUpdate,
    EnvejecimientoCarteraItem,
    EnvejecimientoCarteraResponse,
    LibroDiarioItem,
    LibroMayorItem,
    PagoCreate,
    PagoResponse,
    PagoUpdate,
    PeriodoFiscalCreate,
    PeriodoFiscalResponse,
    PeriodoFiscalUpdate,
)

router = APIRouter(prefix="/accounting", tags=["Contabilidad"])


# ==========================================
# Helper functions
# ==========================================

def _check_company_access(user: User, company_id: str) -> None:
    """Verifica que el usuario tenga acceso a la empresa"""
    company_ids = [c.id for c in user.companies] if user.companies else []
    if company_id not in company_ids:
        raise HTTPException(status_code=403, detail="Sin acceso a esta empresa")


def _get_company_id_for_user(user: User) -> str:
    """Obtiene el company_id del primer empresa activa del usuario"""
    if not user.companies:
        raise HTTPException(status_code=400, detail="Usuario sin empresa configurada")
    active = [c for c in user.companies if c.is_active]
    if not active:
        raise HTTPException(status_code=400, detail="No hay empresas activas")
    return active[0].id


async def _check_periodo_abierto(db: AsyncSession, company_id: str, fecha: datetime) -> PeriodoFiscal | None:
    """Verifica que el período fiscal esté abierto para la fecha dada"""
    result = await db.scalar(
        select(PeriodoFiscal).where(
            and_(
                PeriodoFiscal.company_id == company_id,
                PeriodoFiscal.estado == PeriodoFiscalEstado.ABIERTO,
                PeriodoFiscal.fecha_inicio <= fecha,
                PeriodoFiscal.fecha_fin >= fecha,
            )
        )
    )
    return result


# ==========================================
# Plan de Cuentas
# ==========================================

@router.get("/cuentas-contables", response_model=list[CuentaContableResponse])
async def listar_cuentas_contables(
    company_id: Optional[str] = None,
    tipo: Optional[str] = None,
    nivel: Optional[int] = None,
    es_imputable: Optional[bool] = None,
    search: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista las cuentas contables de la empresa"""
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    conditions = [CuentaContable.company_id == cid, CuentaContable.is_active == True]
    if tipo:
        conditions.append(CuentaContable.tipo == tipo)
    if nivel is not None:
        conditions.append(CuentaContable.nivel == nivel)
    if es_imputable is not None:
        conditions.append(CuentaContable.es_imputable == es_imputable)
    if search:
        conditions.append(
            (CuentaContable.codigo.ilike(f"%{search}%")) |
            (CuentaContable.nombre.ilike(f"%{search}%"))
        )

    result = await db.scalars(
        select(CuentaContable)
        .where(and_(*conditions))
        .order_by(CuentaContable.codigo)
    )
    cuentas = result.all()

    response = []
    for c in cuentas:
        r = CuentaContableResponse.model_validate(c)
        r.codigo_nombre = c.codigo_nombre
        response.append(r)
    return response


@router.post("/cuentas-contables", response_model=CuentaContableResponse, status_code=201)
async def crear_cuenta_contable(
    data: CuentaContableCreate,
    company_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea una nueva cuenta contable"""
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    # Validate tipo
    valid_tipos = [t.value for t in TipoCuentaContable]
    if data.tipo not in valid_tipos:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Válidos: {valid_tipos}")

    # Validate naturaleza
    valid_nat = [n.value for n in NaturalezaCuenta]
    if data.naturaleza not in valid_nat:
        raise HTTPException(status_code=400, detail=f"Naturaleza inválida. Válidas: {valid_nat}")

    # Check duplicate code
    existing = await db.scalar(
        select(CuentaContable).where(
            and_(CuentaContable.company_id == cid, CuentaContable.codigo == data.codigo)
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe una cuenta con código {data.codigo}")

    cuenta = CuentaContable(
        company_id=cid,
        **data.model_dump(),
    )
    db.add(cuenta)
    await db.commit()
    await db.refresh(cuenta)

    r = CuentaContableResponse.model_validate(cuenta)
    r.codigo_nombre = cuenta.codigo_nombre
    return r


@router.put("/cuentas-contables/{cuenta_id}", response_model=CuentaContableResponse)
async def actualizar_cuenta_contable(
    cuenta_id: str,
    data: CuentaContableUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza una cuenta contable"""
    cuenta_id = validate_uuid(cuenta_id, "cuenta_id")
    cuenta = await db.get(CuentaContable, cuenta_id)
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta contable no encontrada")
    _check_company_access(user, cuenta.company_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cuenta, field, value)

    await db.commit()
    await db.refresh(cuenta)

    r = CuentaContableResponse.model_validate(cuenta)
    r.codigo_nombre = cuenta.codigo_nombre
    return r


@router.delete("/cuentas-contables/{cuenta_id}")
async def eliminar_cuenta_contable(
    cuenta_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Elimina (desactiva) una cuenta contable"""
    cuenta_id = validate_uuid(cuenta_id, "cuenta_id")
    cuenta = await db.get(CuentaContable, cuenta_id)
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta contable no encontrada")
    _check_company_access(user, cuenta.company_id)

    # Check no asientos referencing this account
    count = await db.scalar(
        select(func.count(AsientoDetalle.id)).where(AsientoDetalle.cuenta_contable_id == cuenta_id)
    )
    if count > 0:
        raise HTTPException(status_code=400, detail="No se puede eliminar: tiene asientos asociados")

    cuenta.is_active = False
    await db.commit()
    return {"detail": "Cuenta contable desactivada"}


def _load_catalogo_oficial() -> list[dict]:
    """Carga el catálogo oficial de cuentas contables Ecuador 2026 desde JSON."""
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    json_path = os.path.join(data_dir, "catalogo_cuentas_ecuador_2026.json")
    if not os.path.exists(json_path):
        # Try relative to backend root
        json_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "catalogo_cuentas_ecuador_2026.json")
    if not os.path.exists(json_path):
        raise HTTPException(
            status_code=500,
            detail="Archivo de catálogo oficial no encontrado. Contacte al administrador."
        )
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/catalogo-oficial")
async def catalogo_oficial(
    user: User = Depends(get_current_user),
):
    """Devuelve el catálogo oficial de cuentas contables Ecuador 2026.

    Retorna todas las cuentas del catálogo del MEF para usar como
    selector al crear cuentas contables manualmente.
    """
    return _load_catalogo_oficial()


@router.post("/cuentas-contables/seed-default/{company_id}")
async def seed_plan_cuentas_default(
    company_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Genera el Plan de Cuentas por defecto para una empresa.

    Carga el Catálogo General de Cuentas Contables del Sector Público
    No Financiero del Ecuador (Enero 2026) desde el archivo oficial.
    Total: ~3,633 cuentas contables.
    """
    company_id = validate_uuid(company_id, "company_id")
    _check_company_access(user, company_id)

    # Check if already has accounts
    count = await db.scalar(
        select(func.count(CuentaContable.id)).where(CuentaContable.company_id == company_id)
    )
    if count > 0:
        raise HTTPException(status_code=400, detail="La empresa ya tiene cuentas contables")

    # Load official catalog from JSON
    catalogo = _load_catalogo_oficial()

    # Build a lookup for parent accounts (code -> CuentaContable)
    parent_map: dict[str, CuentaContable] = {}
    cuentas_creadas = []

    # Sort by code to ensure parents are created before children
    catalogo.sort(key=lambda a: [int(x) for x in a["code"].split(".")])

    for entry in catalogo:
        codigo = entry["code"]
        nombre = entry["name"]
        tipo = entry.get("tipo", "activo")
        naturaleza = entry.get("naturaleza", "deudora")
        nivel = entry.get("level", 1)

        # Determine parent code (everything except the last segment)
        parts = codigo.split(".")
        if len(parts) > 1:
            parent_code = ".".join(parts[:-1])
        else:
            parent_code = None

        cuenta = CuentaContable(
            company_id=company_id,
            codigo=codigo,
            nombre=nombre,
            tipo=tipo,
            naturaleza=naturaleza,
            nivel=nivel,
            cuenta_padre_id=parent_map[parent_code].id if parent_code and parent_code in parent_map else None,
            es_cuenta_movimiento=(nivel >= 3),
            es_imputable=(nivel >= 3),
            saldo_inicial=Decimal("0"),
            saldo_actual=Decimal("0"),
            total_debitos=Decimal("0"),
            total_creditos=Decimal("0"),
        )
        db.add(cuenta)
        parent_map[codigo] = cuenta
        cuentas_creadas.append(cuenta)

    await db.flush()  # Flush to get IDs for parent references in subsequent batches
    await db.commit()
    return {"detail": f"Se crearon {len(cuentas_creadas)} cuentas contables del catálogo oficial del Ecuador 2026"}


# ==========================================
# Asientos Contables
# ==========================================

@router.get("/asientos-contables", response_model=list[AsientoContableResponse])
async def listar_asientos(
    company_id: Optional[str] = None,
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista asientos contables"""
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    conditions = [AsientoContable.company_id == cid, AsientoContable.is_active == True]
    if estado:
        conditions.append(AsientoContable.estado == estado)
    if tipo:
        conditions.append(AsientoContable.tipo == tipo)
    if fecha_desde:
        conditions.append(AsientoContable.fecha >= fecha_desde)
    if fecha_hasta:
        conditions.append(AsientoContable.fecha <= fecha_hasta)
    if search:
        conditions.append(
            (AsientoContable.numero.ilike(f"%{search}%")) |
            (AsientoContable.concepto.ilike(f"%{search}%"))
        )

    result = await db.scalars(
        select(AsientoContable)
        .where(and_(*conditions))
        .order_by(AsientoContable.fecha.desc(), AsientoContable.numero.desc())
        .offset(skip)
        .limit(limit)
    )
    asientos = result.all()

    response = []
    for a in asientos:
        r = AsientoContableResponse.model_validate(a)
        r.is_cuadrado = a.is_cuadrado
        # Add cuenta info to detalles
        for d in r.detalles:
            detalle_obj = next((dd for dd in a.detalles if dd.id == d.id), None)
            if detalle_obj and detalle_obj.cuenta_contable:
                d.cuenta_codigo = detalle_obj.cuenta_contable.codigo
                d.cuenta_nombre = detalle_obj.cuenta_contable.nombre
        response.append(r)
    return response


@router.post("/asientos-contables", response_model=AsientoContableResponse, status_code=201)
async def crear_asiento(
    data: AsientoContableCreate,
    company_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea un asiento contable con partida doble"""
    data.referencia_id = clean_uuid_param(data.referencia_id, "referencia_id")
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    # Validate: at least 2 detail lines
    if len(data.detalles) < 2:
        raise HTTPException(status_code=400, detail="Un asiento debe tener al menos 2 líneas")

    # Validate: debits must equal credits
    total_debitos = sum(d.debito for d in data.detalles)
    total_creditos = sum(d.credito for d in data.detalles)
    if total_debitos != total_creditos:
        raise HTTPException(
            status_code=400,
            detail=f"Asiento descuadrado: débitos={total_debitos}, créditos={total_creditos}"
        )

    # Validate: each line must have either debit OR credit, not both
    for d in data.detalles:
        if d.debito > 0 and d.credito > 0:
            raise HTTPException(status_code=400, detail="Una línea no puede tener débito y crédito simultáneamente")
        if d.debito == 0 and d.credito == 0:
            raise HTTPException(status_code=400, detail="Una línea debe tener débito o crédito")

    # Validate: cuentas contables exist
    cuenta_ids = [d.cuenta_contable_id for d in data.detalles]
    for cid_item in cuenta_ids:
        cuenta = await db.get(CuentaContable, cid_item)
        if not cuenta or not cuenta.es_imputable:
            raise HTTPException(status_code=400, detail=f"Cuenta contable {cid_item} no encontrada o no imputable")

    # Check periodo fiscal
    periodo = await _check_periodo_abierto(db, cid, data.fecha)
    if periodo is None:
        # Auto-create period if not exists
        anio = data.fecha.year
        mes = data.fecha.month
        periodo = PeriodoFiscal(
            company_id=cid,
            user_id=user.id,
            nombre=f"Mes {mes:02d}/{anio}",
            anio=anio,
            mes=mes,
            tipo_periodo="mensual",
            fecha_inicio=datetime(anio, mes, 1, tzinfo=timezone.utc),
            fecha_fin=datetime(anio, mes, 28, 23, 59, 59, tzinfo=timezone.utc),
        )
        db.add(periodo)
        await db.flush()

    # Get company for sequential
    from app.models.company import Company
    company = await db.get(Company, cid)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    numero = f"AS-{str(company.secuencial_asiento).zfill(6)}"
    company.secuencial_asiento += 1

    asiento = AsientoContable(
        company_id=cid,
        user_id=user.id,
        periodo_fiscal_id=periodo.id,
        numero=numero,
        fecha=data.fecha,
        tipo=data.tipo,
        estado=AsientoEstado.BORRADOR,
        total_debitos=total_debitos,
        total_creditos=total_creditos,
        concepto=data.concepto,
        referencia_tipo=data.referencia_tipo,
        referencia_id=data.referencia_id,
        referencia_secuencial=data.referencia_secuencial,
        observaciones=data.observaciones,
    )
    db.add(asiento)
    await db.flush()

    # Create detalles
    for d in data.detalles:
        detalle = AsientoDetalle(
            asiento_id=asiento.id,
            cuenta_contable_id=d.cuenta_contable_id,
            debito=d.debito,
            credito=d.credito,
            descripcion=d.descripcion,
            referencia_tipo=d.referencia_tipo,
            referencia_id=d.referencia_id,
        )
        db.add(detalle)

        # Update cuenta contable saldo
        cuenta = await db.get(CuentaContable, d.cuenta_contable_id)
        if cuenta:
            cuenta.total_debitos += d.debito
            cuenta.total_creditos += d.credito
            if cuenta.naturaleza == "deudora":
                cuenta.saldo_actual = cuenta.saldo_inicial + cuenta.total_debitos - cuenta.total_creditos
            else:
                cuenta.saldo_actual = cuenta.saldo_inicial + cuenta.total_creditos - cuenta.total_debitos

    await db.commit()
    await db.refresh(asiento)

    r = AsientoContableResponse.model_validate(asiento)
    r.is_cuadrado = asiento.is_cuadrado
    return r


@router.put("/asientos-contables/{asiento_id}", response_model=AsientoContableResponse)
async def actualizar_asiento(
    asiento_id: str,
    data: AsientoContableUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza un asiento contable (solo en borrador)"""
    asiento_id = validate_uuid(asiento_id, "asiento_id")
    asiento = await db.get(AsientoContable, asiento_id)
    if not asiento:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    _check_company_access(user, asiento.company_id)

    if asiento.estado != AsientoEstado.BORRADOR:
        raise HTTPException(status_code=400, detail="Solo se pueden modificar asientos en borrador")

    for field, value in data.model_dump(exclude_unset=True).items():
        if field != "detalles":
            setattr(asiento, field, value)

    if data.detalles is not None:
        # Validate debits = credits
        total_debitos = sum(d.debito for d in data.detalles)
        total_creditos = sum(d.credito for d in data.detalles)
        if total_debitos != total_creditos:
            raise HTTPException(status_code=400, detail="Asiento descuadrado")

        # Delete old detalles and reverse saldos
        for old_d in asiento.detalles:
            cuenta = await db.get(CuentaContable, old_d.cuenta_contable_id)
            if cuenta:
                cuenta.total_debitos -= old_d.debito
                cuenta.total_creditos -= old_d.credito
                if cuenta.naturaleza == "deudora":
                    cuenta.saldo_actual = cuenta.saldo_inicial + cuenta.total_debitos - cuenta.total_creditos
                else:
                    cuenta.saldo_actual = cuenta.saldo_inicial + cuenta.total_creditos - cuenta.total_debitos
            await db.delete(old_d)

        # Create new detalles
        for d in data.detalles:
            detalle = AsientoDetalle(
                asiento_id=asiento.id,
                cuenta_contable_id=d.cuenta_contable_id,
                debito=d.debito,
                credito=d.credito,
                descripcion=d.descripcion,
            )
            db.add(detalle)
            cuenta = await db.get(CuentaContable, d.cuenta_contable_id)
            if cuenta:
                cuenta.total_debitos += d.debito
                cuenta.total_creditos += d.credito
                if cuenta.naturaleza == "deudora":
                    cuenta.saldo_actual = cuenta.saldo_inicial + cuenta.total_debitos - cuenta.total_creditos
                else:
                    cuenta.saldo_actual = cuenta.saldo_inicial + cuenta.total_creditos - cuenta.total_debitos

        asiento.total_debitos = total_debitos
        asiento.total_creditos = total_creditos

    await db.commit()
    await db.refresh(asiento)

    r = AsientoContableResponse.model_validate(asiento)
    r.is_cuadrado = asiento.is_cuadrado
    return r


@router.post("/asientos-contables/{asiento_id}/aprobar")
async def aprobar_asiento(
    asiento_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aprueba un asiento contable"""
    asiento_id = validate_uuid(asiento_id, "asiento_id")
    asiento = await db.get(AsientoContable, asiento_id)
    if not asiento:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    _check_company_access(user, asiento.company_id)

    if asiento.estado != AsientoEstado.BORRADOR:
        raise HTTPException(status_code=400, detail="Solo se pueden aprobar asientos en borrador")

    if not asiento.is_cuadrado:
        raise HTTPException(status_code=400, detail="El asiento no está cuadrado")

    asiento.estado = AsientoEstado.APROBADO
    await db.commit()
    return {"detail": "Asiento aprobado"}


@router.post("/asientos-contables/{asiento_id}/anular")
async def anular_asiento(
    asiento_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Anula un asiento contable y revierte saldos"""
    asiento_id = validate_uuid(asiento_id, "asiento_id")
    asiento = await db.get(AsientoContable, asiento_id)
    if not asiento:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    _check_company_access(user, asiento.company_id)

    if asiento.estado == AsientoEstado.ANULADO:
        raise HTTPException(status_code=400, detail="El asiento ya está anulado")

    # Reverse saldos
    for d in asiento.detalles:
        cuenta = await db.get(CuentaContable, d.cuenta_contable_id)
        if cuenta:
            cuenta.total_debitos -= d.debito
            cuenta.total_creditos -= d.credito
            if cuenta.naturaleza == "deudora":
                cuenta.saldo_actual = cuenta.saldo_inicial + cuenta.total_debitos - cuenta.total_creditos
            else:
                cuenta.saldo_actual = cuenta.saldo_inicial + cuenta.total_creditos - cuenta.total_debitos

    asiento.estado = AsientoEstado.ANULADO
    await db.commit()
    return {"detail": "Asiento anulado y saldos revertidos"}


# ==========================================
# Cuentas por Cobrar
# ==========================================

@router.get("/cuentas-por-cobrar", response_model=list[CuentaPorCobrarResponse])
async def listar_cuentas_por_cobrar(
    company_id: Optional[str] = None,
    estado: Optional[str] = None,
    client_id: Optional[str] = None,
    vencidas: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista cuentas por cobrar"""
    client_id = clean_uuid_param(client_id, "client_id")
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    conditions = [CuentaPorCobrar.company_id == cid, CuentaPorCobrar.is_active == True]
    if estado:
        conditions.append(CuentaPorCobrar.estado == estado)
    if client_id:
        conditions.append(CuentaPorCobrar.client_id == client_id)
    if vencidas:
        conditions.append(CuentaPorCobrar.estado.in_([
            CuentaPorCobrarEstado.VENCIDA,
            CuentaPorCobrarEstado.EN_COBRANZA,
        ]))

    result = await db.scalars(
        select(CuentaPorCobrar)
        .where(and_(*conditions))
        .order_by(CuentaPorCobrar.fecha_vencimiento)
        .offset(skip)
        .limit(limit)
    )
    items = result.all()

    # Update dias_vencida
    now = datetime.now(timezone.utc)
    response = []
    for item in items:
        if item.fecha_vencimiento:
            item.dias_vencida = max(0, (now - item.fecha_vencimiento).days)
            # Update estado if vencida
            if item.estado == CuentaPorCobrarEstado.PENDIENTE and item.dias_vencida > 0:
                item.estado = CuentaPorCobrarEstado.VENCIDA
        r = CuentaPorCobrarResponse.model_validate(item)
        r.rango_vencimiento = item.rango_vencimiento
        response.append(r)

    await db.commit()
    return response


@router.post("/cuentas-por-cobrar", response_model=CuentaPorCobrarResponse, status_code=201)
async def crear_cuenta_por_cobrar(
    data: CuentaPorCobrarCreate,
    company_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea una cuenta por cobrar"""
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    cxc = CuentaPorCobrar(
        company_id=cid,
        user_id=user.id,
        **data.model_dump(),
        monto_pagado=Decimal("0"),
        monto_pendiente=data.monto_total,
        estado=CuentaPorCobrarEstado.PENDIENTE,
        dias_vencida=0,
    )
    db.add(cxc)
    await db.commit()
    await db.refresh(cxc)

    r = CuentaPorCobrarResponse.model_validate(cxc)
    r.rango_vencimiento = cxc.rango_vencimiento
    return r


@router.put("/cuentas-por-cobrar/{cxc_id}", response_model=CuentaPorCobrarResponse)
async def actualizar_cuenta_por_cobrar(
    cxc_id: str,
    data: CuentaPorCobrarUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualiza una cuenta por cobrar"""
    cxc_id = validate_uuid(cxc_id, "cxc_id")
    cxc = await db.get(CuentaPorCobrar, cxc_id)
    if not cxc:
        raise HTTPException(status_code=404, detail="Cuenta por cobrar no encontrada")
    _check_company_access(user, cxc.company_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cxc, field, value)

    await db.commit()
    await db.refresh(cxc)

    r = CuentaPorCobrarResponse.model_validate(cxc)
    r.rango_vencimiento = cxc.rango_vencimiento
    return r


@router.get("/cuentas-por-cobrar/envejecimiento", response_model=EnvejecimientoCarteraResponse)
async def envejecimiento_cartera(
    company_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene el envejecimiento de cartera (CxC agrupado por cliente y rango)"""
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    cxcs = await db.scalars(
        select(CuentaPorCobrar).where(
            and_(
                CuentaPorCobrar.company_id == cid,
                CuentaPorCobrar.is_active == True,
                CuentaPorCobrar.estado != CuentaPorCobrarEstado.PAGADA,
            )
        )
    )
    items_list = cxcs.all()

    now = datetime.now(timezone.utc)
    grouped: dict[str, EnvejecimientoCarteraItem] = {}

    for cxc in items_list:
        key = cxc.cliente_identificacion or cxc.cliente_nombre or "SIN_NOMBRE"
        if key not in grouped:
            grouped[key] = EnvejecimientoCarteraItem(
                cliente_id=cxc.client_id,
                cliente_nombre=cxc.cliente_nombre or "Sin nombre",
                cliente_identificacion=cxc.cliente_identificacion,
            )

        item = grouped[key]
        item.total += cxc.monto_pendiente

        # Calculate aging
        dias = 0
        if cxc.fecha_vencimiento:
            dias = max(0, (now - cxc.fecha_vencimiento).days)

        if dias <= 0:
            item.vigente += cxc.monto_pendiente
        elif dias <= 30:
            item.dias_1_30 += cxc.monto_pendiente
        elif dias <= 60:
            item.dias_31_60 += cxc.monto_pendiente
        elif dias <= 90:
            item.dias_61_90 += cxc.monto_pendiente
        elif dias <= 180:
            item.dias_91_180 += cxc.monto_pendiente
        else:
            item.dias_mas_180 += cxc.monto_pendiente

    response = EnvejecimientoCarteraResponse(items=list(grouped.values()))
    for item in response.items:
        response.total_general += item.total
        response.total_vigente += item.vigente
        response.total_1_30 += item.dias_1_30
        response.total_31_60 += item.dias_31_60
        response.total_61_90 += item.dias_61_90
        response.total_91_180 += item.dias_91_180
        response.total_mas_180 += item.dias_mas_180

    return response


# ==========================================
# Pagos / Cobros
# ==========================================

@router.get("/pagos", response_model=list[PagoResponse])
async def listar_pagos(
    company_id: Optional[str] = None,
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista pagos/cobros"""
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    conditions = [Pago.company_id == cid, Pago.is_active == True]
    if tipo:
        conditions.append(Pago.tipo == tipo)
    if estado:
        conditions.append(Pago.estado == estado)
    if fecha_desde:
        conditions.append(Pago.fecha >= fecha_desde)
    if fecha_hasta:
        conditions.append(Pago.fecha <= fecha_hasta)

    result = await db.scalars(
        select(Pago)
        .where(and_(*conditions))
        .order_by(Pago.fecha.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.all()


@router.post("/pagos", response_model=PagoResponse, status_code=201)
async def crear_pago(
    data: PagoCreate,
    company_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registra un pago/cobro"""
    data.cuenta_bancaria_id = clean_uuid_param(data.cuenta_bancaria_id, "cuenta_bancaria_id")
    data.cuenta_por_cobrar_id = clean_uuid_param(data.cuenta_por_cobrar_id, "cuenta_por_cobrar_id")
    data.cuenta_por_pagar_id = clean_uuid_param(data.cuenta_por_pagar_id, "cuenta_por_pagar_id")
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    # Generate sequential number
    from app.models.company import Company
    company = await db.get(Company, cid)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    tipo_prefix = "COB" if data.tipo == PagoTipo.COBRO else "PAG"
    numero = f"{tipo_prefix}-{str(company.secuencial_asiento).zfill(6)}"
    company.secuencial_asiento += 1

    pago = Pago(
        company_id=cid,
        user_id=user.id,
        tipo=data.tipo,
        numero=numero,
        fecha=data.fecha,
        monto=data.monto,
        forma_pago=data.forma_pago,
        referencia=data.referencia,
        cuenta_bancaria_id=data.cuenta_bancaria_id,
        cuenta_por_cobrar_id=data.cuenta_por_cobrar_id,
        cuenta_por_pagar_id=data.cuenta_por_pagar_id,
        tercero_nombre=data.tercero_nombre,
        tercero_identificacion=data.tercero_identificacion,
        estado=PagoEstado.PENDIENTE,
        observaciones=data.observaciones,
    )
    db.add(pago)

    # Update CxC or CxP
    if data.cuenta_por_cobrar_id and data.tipo == PagoTipo.COBRO:
        cxc = await db.get(CuentaPorCobrar, data.cuenta_por_cobrar_id)
        if cxc:
            cxc.monto_pagado += data.monto
            cxc.monto_pendiente -= data.monto
            if cxc.monto_pendiente <= Decimal("0"):
                cxc.monto_pendiente = Decimal("0")
                cxc.estado = CuentaPorCobrarEstado.PAGADA
            else:
                cxc.estado = CuentaPorCobrarEstado.PARCIALMENTE_PAGADA

    if data.cuenta_por_pagar_id and data.tipo == PagoTipo.PAGO:
        cxp = await db.get(CuentaPorPagar, data.cuenta_por_pagar_id)
        if cxp:
            cxp.monto_pagado += data.monto
            cxp.monto_pendiente -= data.monto
            if cxp.monto_pendiente <= Decimal("0"):
                cxp.monto_pendiente = Decimal("0")
                cxp.estado = "pagada"
            else:
                cxp.estado = "parcialmente_pagada"

    await db.commit()
    await db.refresh(pago)
    return pago


@router.post("/pagos/{pago_id}/confirmar")
async def confirmar_pago(
    pago_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirma un pago/cobro"""
    pago_id = validate_uuid(pago_id, "pago_id")
    pago = await db.get(Pago, pago_id)
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    _check_company_access(user, pago.company_id)

    pago.estado = PagoEstado.CONFIRMADO
    await db.commit()
    return {"detail": "Pago confirmado"}


@router.post("/pagos/{pago_id}/anular")
async def anular_pago(
    pago_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Anula un pago/cobro y revierte montos"""
    pago_id = validate_uuid(pago_id, "pago_id")
    pago = await db.get(Pago, pago_id)
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    _check_company_access(user, pago.company_id)

    # Reverse CxC
    if pago.cuenta_por_cobrar_id:
        cxc = await db.get(CuentaPorCobrar, pago.cuenta_por_cobrar_id)
        if cxc:
            cxc.monto_pagado -= pago.monto
            cxc.monto_pendiente += pago.monto
            if cxc.estado == CuentaPorCobrarEstado.PAGADA:
                cxc.estado = CuentaPorCobrarEstado.PARCIALMENTE_PAGADA

    # Reverse CxP
    if pago.cuenta_por_pagar_id:
        cxp = await db.get(CuentaPorPagar, pago.cuenta_por_pagar_id)
        if cxp:
            cxp.monto_pagado -= pago.monto
            cxp.monto_pendiente += pago.monto
            if cxp.estado == "pagada":
                cxp.estado = "parcialmente_pagada"

    pago.estado = PagoEstado.ANULADO
    await db.commit()
    return {"detail": "Pago anulado y montos revertidos"}


# ==========================================
# Períodos Fiscales
# ==========================================

@router.get("/periodos-fiscales", response_model=list[PeriodoFiscalResponse])
async def listar_periodos_fiscales(
    company_id: Optional[str] = None,
    estado: Optional[str] = None,
    anio: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista períodos fiscales"""
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    conditions = [PeriodoFiscal.company_id == cid, PeriodoFiscal.is_active == True]
    if estado:
        conditions.append(PeriodoFiscal.estado == estado)
    if anio:
        conditions.append(PeriodoFiscal.anio == anio)

    result = await db.scalars(
        select(PeriodoFiscal)
        .where(and_(*conditions))
        .order_by(PeriodoFiscal.fecha_inicio.desc())
    )
    return result.all()


@router.post("/periodos-fiscales", response_model=PeriodoFiscalResponse, status_code=201)
async def crear_periodo_fiscal(
    data: PeriodoFiscalCreate,
    company_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crea un período fiscal"""
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    # Check for overlapping period
    existing = await db.scalar(
        select(PeriodoFiscal).where(
            and_(
                PeriodoFiscal.company_id == cid,
                PeriodoFiscal.fecha_inicio <= data.fecha_fin,
                PeriodoFiscal.fecha_fin >= data.fecha_inicio,
            )
        )
    )
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un período que se solapa con las fechas indicadas")

    periodo = PeriodoFiscal(
        company_id=cid,
        user_id=user.id,
        **data.model_dump(),
        estado=PeriodoFiscalEstado.ABIERTO,
    )
    db.add(periodo)
    await db.commit()
    await db.refresh(periodo)
    return periodo


@router.post("/periodos-fiscales/{periodo_id}/cerrar")
async def cerrar_periodo_fiscal(
    periodo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cierra un período fiscal - impide crear/modificar asientos en ese período"""
    periodo_id = validate_uuid(periodo_id, "periodo_id")
    periodo = await db.get(PeriodoFiscal, periodo_id)
    if not periodo:
        raise HTTPException(status_code=404, detail="Período fiscal no encontrado")
    _check_company_access(user, periodo.company_id)

    if periodo.estado == PeriodoFiscalEstado.CERRADO:
        raise HTTPException(status_code=400, detail="El período ya está cerrado")

    # Count asientos in this period
    count = await db.scalar(
        select(func.count(AsientoContable.id)).where(
            and_(
                AsientoContable.company_id == periodo.company_id,
                AsientoContable.fecha >= periodo.fecha_inicio,
                AsientoContable.fecha <= periodo.fecha_fin,
                AsientoContable.estado == AsientoEstado.BORRADOR,
            )
        )
    )
    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Hay {count} asientos en borrador en este período. Apruebe o anule antes de cerrar."
        )

    # Calculate totals
    result = await db.execute(
        select(
            func.coalesce(func.sum(AsientoContable.total_debitos), 0),
            func.coalesce(func.sum(AsientoContable.total_creditos), 0),
            func.count(AsientoContable.id),
        ).where(
            and_(
                AsientoContable.company_id == periodo.company_id,
                AsientoContable.fecha >= periodo.fecha_inicio,
                AsientoContable.fecha <= periodo.fecha_fin,
                AsientoContable.estado == AsientoEstado.APROBADO,
            )
        )
    )
    row = result.one()
    periodo.total_debitos = row[0]
    periodo.total_creditos = row[1]
    periodo.total_asientos = row[2]
    periodo.estado = PeriodoFiscalEstado.CERRADO
    periodo.fecha_cierre = datetime.now(timezone.utc)
    periodo.cerrado_por = user.id

    await db.commit()
    return {"detail": f"Período {periodo.nombre} cerrado exitosamente"}


@router.post("/periodos-fiscales/{periodo_id}/reabrir")
async def reabrir_periodo_fiscal(
    periodo_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reabre un período fiscal cerrado"""
    periodo_id = validate_uuid(periodo_id, "periodo_id")
    periodo = await db.get(PeriodoFiscal, periodo_id)
    if not periodo:
        raise HTTPException(status_code=404, detail="Período fiscal no encontrado")
    _check_company_access(user, periodo.company_id)

    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Solo el administrador puede reabrir períodos")

    periodo.estado = PeriodoFiscalEstado.ABIERTO
    periodo.fecha_cierre = None
    periodo.cerrado_por = None

    await db.commit()
    return {"detail": f"Período {periodo.nombre} reabierto"}


# ==========================================
# Reportes Contables
# ==========================================

@router.get("/balance-comprobacion", response_model=BalanceComprobacionResponse)
async def balance_comprobacion(
    company_id: Optional[str] = None,
    anio: Optional[int] = None,
    mes: Optional[int] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Genera el Balance de Comprobación"""
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    cuentas = await db.scalars(
        select(CuentaContable).where(
            and_(CuentaContable.company_id == cid, CuentaContable.is_active == True)
        ).order_by(CuentaContable.codigo)
    )

    items = []
    total_debitos = Decimal("0")
    total_creditos = Decimal("0")
    total_saldo_deudor = Decimal("0")
    total_saldo_acreedor = Decimal("0")

    for c in cuentas.all():
        saldo_deudor = Decimal("0")
        saldo_acreedor = Decimal("0")
        if c.naturaleza == "deudora":
            if c.saldo_actual >= 0:
                saldo_deudor = c.saldo_actual
            else:
                saldo_acreedor = abs(c.saldo_actual)
        else:
            if c.saldo_actual >= 0:
                saldo_acreedor = c.saldo_actual
            else:
                saldo_deudor = abs(c.saldo_actual)

        items.append(BalanceComprobacionItem(
            codigo=c.codigo,
            nombre=c.nombre,
            tipo=c.tipo,
            nivel=c.nivel,
            saldo_deudor=saldo_deudor,
            saldo_acreedor=saldo_acreedor,
            total_debitos=c.total_debitos,
            total_creditos=c.total_creditos,
        ))
        total_debitos += c.total_debitos
        total_creditos += c.total_creditos
        total_saldo_deudor += saldo_deudor
        total_saldo_acreedor += saldo_acreedor

    return BalanceComprobacionResponse(
        items=items,
        total_debitos=total_debitos,
        total_creditos=total_creditos,
        total_saldo_deudor=total_saldo_deudor,
        total_saldo_acreedor=total_saldo_acreedor,
        periodo=f"{mes:02d}/{anio}" if mes and anio else str(anio) if anio else "Acumulado",
    )


@router.get("/libro-diario", response_model=list[LibroDiarioItem])
async def libro_diario(
    company_id: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Genera el Libro Diario"""
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    conditions = [
        AsientoContable.company_id == cid,
        AsientoContable.is_active == True,
        AsientoContable.estado == AsientoEstado.APROBADO,
    ]
    if fecha_desde:
        conditions.append(AsientoContable.fecha >= fecha_desde)
    if fecha_hasta:
        conditions.append(AsientoContable.fecha <= fecha_hasta)

    asientos = await db.scalars(
        select(AsientoContable)
        .where(and_(*conditions))
        .order_by(AsientoContable.fecha, AsientoContable.numero)
        .offset(skip)
        .limit(limit)
    )

    items = []
    for a in asientos.all():
        for d in a.detalles:
            cuenta_codigo = d.cuenta_contable.codigo if d.cuenta_contable else ""
            cuenta_nombre = d.cuenta_contable.nombre if d.cuenta_contable else ""
            items.append(LibroDiarioItem(
                asiento_numero=a.numero,
                asiento_fecha=a.fecha,
                asiento_concepto=a.concepto,
                asiento_tipo=a.tipo,
                asiento_estado=a.estado,
                cuenta_codigo=cuenta_codigo,
                cuenta_nombre=cuenta_nombre,
                debito=d.debito,
                credito=d.credito,
                descripcion=d.descripcion,
            ))
    return items


@router.get("/libro-mayor/{cuenta_id}", response_model=LibroMayorItem)
async def libro_mayor(
    cuenta_id: str,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Genera el Libro Mayor para una cuenta contable"""
    cuenta_id = validate_uuid(cuenta_id, "cuenta_id")
    cuenta = await db.get(CuentaContable, cuenta_id)
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta contable no encontrada")
    _check_company_access(user, cuenta.company_id)

    # Get all detalles for this account
    conditions = [AsientoDetalle.cuenta_contable_id == cuenta_id]
    if fecha_desde or fecha_hasta:
        # Join with asiento for date filter
        subq = select(AsientoContable.id).where(
            and_(
                AsientoContable.company_id == cuenta.company_id,
                AsientoContable.estado == AsientoEstado.APROBADO,
            )
        )
        if fecha_desde:
            subq = subq.where(AsientoContable.fecha >= fecha_desde)
        if fecha_hasta:
            subq = subq.where(AsientoContable.fecha <= fecha_hasta)

    detalles = await db.scalars(
        select(AsientoDetalle)
        .where(AsientoDetalle.cuenta_contable_id == cuenta_id)
        .order_by(AsientoDetalle.created_at)
    )

    movimientos = []
    total_debitos = Decimal("0")
    total_creditos = Decimal("0")
    for d in detalles.all():
        if d.asiento and d.asiento.estado == AsientoEstado.APROBADO:
            if fecha_desde and d.asiento.fecha < fecha_desde:
                continue
            if fecha_hasta and d.asiento.fecha > fecha_hasta:
                continue
            movimientos.append({
                "fecha": d.asiento.fecha.isoformat(),
                "asiento_numero": d.asiento.numero,
                "concepto": d.asiento.concepto,
                "debito": float(d.debito),
                "credito": float(d.credito),
                "descripcion": d.descripcion,
            })
            total_debitos += d.debito
            total_creditos += d.credito

    if cuenta.naturaleza == "deudora":
        saldo_final = cuenta.saldo_inicial + total_debitos - total_creditos
    else:
        saldo_final = cuenta.saldo_inicial + total_creditos - total_debitos

    return LibroMayorItem(
        cuenta_codigo=cuenta.codigo,
        cuenta_nombre=cuenta.nombre,
        cuenta_tipo=cuenta.tipo,
        saldo_inicial=cuenta.saldo_inicial,
        movimientos=movimientos,
        total_debitos=total_debitos,
        total_creditos=total_creditos,
        saldo_final=saldo_final,
    )


# ==========================================
# Stats
# ==========================================

@router.get("/stats", response_model=ContabilidadStats)
async def contabilidad_stats(
    company_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene estadísticas del módulo contable"""
    company_id = clean_company_id(company_id)
    cid = company_id or _get_company_id_for_user(user)
    _check_company_access(user, cid)

    total_cuentas = await db.scalar(
        select(func.count(CuentaContable.id)).where(CuentaContable.company_id == cid)
    ) or 0
    total_cuentas_activas = await db.scalar(
        select(func.count(CuentaContable.id)).where(
            and_(CuentaContable.company_id == cid, CuentaContable.is_active == True)
        )
    ) or 0
    total_asientos = await db.scalar(
        select(func.count(AsientoContable.id)).where(AsientoContable.company_id == cid)
    ) or 0
    total_asientos_aprobados = await db.scalar(
        select(func.count(AsientoContable.id)).where(
            and_(AsientoContable.company_id == cid, AsientoContable.estado == AsientoEstado.APROBADO)
        )
    ) or 0
    total_cxc = await db.scalar(
        select(func.count(CuentaPorCobrar.id)).where(
            and_(CuentaPorCobrar.company_id == cid, CuentaPorCobrar.estado != CuentaPorCobrarEstado.PAGADA)
        )
    ) or 0
    total_cxc_pendiente = await db.scalar(
        select(func.coalesce(func.sum(CuentaPorCobrar.monto_pendiente), 0)).where(
            and_(CuentaPorCobrar.company_id == cid, CuentaPorCobrar.estado != CuentaPorCobrarEstado.PAGADA)
        )
    ) or Decimal("0")
    total_cxp_pendiente = await db.scalar(
        select(func.coalesce(func.sum(CuentaPorPagar.monto_pendiente), 0)).where(
            and_(CuentaPorPagar.company_id == cid, CuentaPorPagar.estado != "pagada")
        )
    ) or Decimal("0")

    # Cobros/pagos del mes actual
    now = datetime.now(timezone.utc)
    total_cobros_mes = await db.scalar(
        select(func.coalesce(func.sum(Pago.monto), 0)).where(
            and_(
                Pago.company_id == cid,
                Pago.tipo == PagoTipo.COBRO,
                Pago.estado == PagoEstado.CONFIRMADO,
            )
        )
    ) or Decimal("0")
    total_pagos_mes = await db.scalar(
        select(func.coalesce(func.sum(Pago.monto), 0)).where(
            and_(
                Pago.company_id == cid,
                Pago.tipo == PagoTipo.PAGO,
                Pago.estado == PagoEstado.CONFIRMADO,
            )
        )
    ) or Decimal("0")

    periodos_abiertos = await db.scalar(
        select(func.count(PeriodoFiscal.id)).where(
            and_(PeriodoFiscal.company_id == cid, PeriodoFiscal.estado == PeriodoFiscalEstado.ABIERTO)
        )
    ) or 0

    # Current period
    current_period = await db.scalar(
        select(PeriodoFiscal).where(
            and_(
                PeriodoFiscal.company_id == cid,
                PeriodoFiscal.estado == PeriodoFiscalEstado.ABIERTO,
                PeriodoFiscal.fecha_inicio <= now,
                PeriodoFiscal.fecha_fin >= now,
            )
        )
    )

    return ContabilidadStats(
        total_cuentas=total_cuentas,
        total_cuentas_activas=total_cuentas_activas,
        total_asientos=total_asientos,
        total_asientos_aprobados=total_asientos_aprobados,
        total_cxc=total_cxc,
        total_cxc_pendiente=total_cxc_pendiente,
        total_cxp_pendiente=total_cxp_pendiente,
        total_cobros_mes=total_cobros_mes,
        total_pagos_mes=total_pagos_mes,
        periodos_abiertos=periodos_abiertos,
        periodo_actual=current_period.nombre if current_period else None,
    )

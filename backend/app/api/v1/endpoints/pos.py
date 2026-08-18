"""
ContaEC - Endpoints de Punto de Venta (POS)
Sesiones de caja, tickets de venta, arqueos y búsqueda de productos
"""
import io
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_action
from app.core.permissions import effective_owner_id
from app.core.database import async_session_factory, get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.core.utils import ensure_consumidor_final
from app.models.client import Client
from app.models.company import Company
from app.models.kardex import Kardex, KardexTipoMovimiento
from app.models.pos import (
    ArqueoTipo,
    CajaEstado,
    POSArqueo,
    POSCashSession,
    POSTicket,
    POSTicketDetalle,
    TicketEstado,
    TipoVenta,
)
from app.models.product import Product
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.pos import (
    POSArqueoCerrarRequest,
    POSArqueoCerrarResponse,
    POSArqueoCreate,
    POSArqueoReporteResponse,
    POSArqueoResumenItem,
    POSArqueoResumenResponse,
    POSArqueoResponse,
    POSCashSessionClose,
    POSCashSessionCreate,
    POSCashSessionResponse,
    POSCashSessionResumen,
    POSProductSearchResponse,
    POSTicketCreate,
    POSTicketDetalleResponse,
    POSTicketPrintResponse,
    POSTicketResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pos", tags=["Punto de Venta (POS)"])


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
# Facturación electrónica automática (POS → SRI)
# ==========================================

def _map_forma_pago(tipo_venta: str, tarjeta_tipo: str | None) -> str:
    """
    Mapea el tipo de venta del POS al código de forma de pago del SRI (Tabla 23).

    - efectivo -> 01 (Sin utilización del sistema financiero)
    - tarjeta débito -> 16 (Tarjeta de débito)
    - tarjeta crédito -> 18 (Tarjeta de crédito)
    - mixto / crédito / otro -> 01 (efectivo como principal)
    """
    if tipo_venta == "tarjeta":
        return "16" if tarjeta_tipo == "debito" else "18"
    return "01"


async def _get_or_create_pos_client(
    db: AsyncSession,
    company_id: str,
    data,
) -> Client:
    """
    Obtiene (o crea) el cliente del comprobante a partir de los datos del ticket POS.

    - Consumidor final (07): usa el cliente automático de la empresa.
    - Otro tipo: busca por identificación; si no existe, lo crea con los datos del ticket.
    """
    tipo_id = (data.cliente_tipo_identificacion or "07").strip()
    if tipo_id == "07":
        return await ensure_consumidor_final(db, company_id)

    identificacion = (data.cliente_identificacion or "").strip()
    if not identificacion:
        return await ensure_consumidor_final(db, company_id)

    result = await db.execute(
        select(Client).where(
            Client.company_id == company_id,
            Client.identificacion == identificacion,
            Client.is_active == True,  # noqa: E712
        ).limit(1)
    )
    client = result.scalars().first()
    if client:
        return client

    client = Client(
        company_id=company_id,
        tipo_identificacion=tipo_id,
        identificacion=identificacion,
        razon_social=(data.cliente_nombre or "CLIENTE").strip()[:255],
        direccion=data.cliente_direccion,
        email=data.cliente_email,
        telefono=data.cliente_telefono,
    )
    db.add(client)
    await db.flush()
    return client


async def _crear_factura_desde_ticket(
    db: AsyncSession,
    ticket,
    data: POSTicketCreate,
    current_user: User,
):
    """
    Genera una factura electrónica (tipo 01) a partir de un ticket POS.

    Devuelve el comprobante creado (estado BORRADOR) o None si no se solicitó.
    La validación, firma y envío al SRI se ejecutan en segundo plano.
    """
    if not data.crear_comprobante:
        return None

    # Imports diferidos para evitar ciclos de importación
    from app.schemas.comprobante import ComprobanteCreate, ComprobanteDetalleCreate
    from app.api.v1.endpoints.comprobantes import create_comprobante as crear_comprobante

    client = await _get_or_create_pos_client(db, data.company_id, data)

    detalles = []
    for det in data.detalles:
        descuento_pct = det.descuento or Decimal("0")
        detalles.append(
            ComprobanteDetalleCreate(
                product_id=det.product_id,
                codigo_principal=det.codigo_principal,
                descripcion=det.descripcion,
                cantidad=det.cantidad,
                unidad_medida=det.unidad_medida or "Unidad",
                precio_unitario=det.precio_unitario,
                descuento=Decimal("0"),
                descuento_tipo="porcentaje",
                descuento_valor=descuento_pct if descuento_pct > 0 else None,
                iva_codigo=det.iva_codigo,
                iva_porcentaje=det.iva_porcentaje,
            )
        )

    info_adicional = {}
    if data.cliente_direccion:
        info_adicional["direccion"] = data.cliente_direccion
    if data.cliente_telefono:
        info_adicional["telefono"] = data.cliente_telefono
    if data.cliente_email:
        info_adicional["email"] = data.cliente_email
    if data.observaciones:
        info_adicional["observaciones"] = data.observaciones
    if data.numero_tarjeta:
        info_adicional["tarjeta"] = f"****{data.numero_tarjeta}"
        if data.tarjeta_marca:
            info_adicional["marca_tarjeta"] = data.tarjeta_marca
        if data.tarjeta_banco:
            info_adicional["banco"] = data.tarjeta_banco

    comp_data = ComprobanteCreate(
        company_id=data.company_id,
        client_id=str(client.id),
        tipo_comprobante="01",
        forma_pago=_map_forma_pago(data.tipo_venta, data.tarjeta_tipo),
        detalles=detalles,
        info_adicional=info_adicional or None,
    )

    comprobante = await crear_comprobante(comp_data, current_user, db)
    ticket.comprobante_id = str(comprobante.id)
    return comprobante


async def _procesar_factura_pos(comprobante_id: str, user_id: str) -> None:
    """
    Ejecuta en segundo plano el pipeline SRI de la factura generada desde el POS:
    validar -> firmar -> enviar/consultar autorización.

    Usa una sesión propia de base de datos y el usuario efectivo (para la firma
    digital en caso de sub-cuentas). Nunca lanza excepciones hacia el cliente.
    """
    from app.api.v1.endpoints.comprobantes import (
        firmar_comprobante,
        procesar_comprobante,
        validar_comprobante,
    )

    try:
        async with async_session_factory() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalars().first()
            if not user:
                logger.warning(f"POS: usuario {user_id} no encontrado al procesar factura {comprobante_id}")
                return

            # 1. Validar (pre-validación SRI)
            try:
                validacion = await validar_comprobante(comprobante_id, user, db)
                if not validacion.get("valid"):
                    logger.warning(
                        f"POS: factura {comprobante_id} no pasó la validación SRI: "
                        f"{validacion.get('errors')}"
                    )
                    return
            except HTTPException as e:
                logger.warning(f"POS: error validando factura {comprobante_id}: {e.detail}")
                return

            # 2. Firmar con la firma electrónica del usuario
            try:
                await firmar_comprobante(comprobante_id, user, db)
            except HTTPException as e:
                logger.warning(
                    f"POS: no se pudo firmar la factura {comprobante_id} "
                    f"(configure la firma electrónica en Configuración): {e.detail}"
                )
                return

            # 3. Enviar al SRI y consultar autorización
            try:
                await procesar_comprobante(comprobante_id, user, db)
            except HTTPException as e:
                logger.warning(f"POS: error al procesar factura {comprobante_id} en el SRI: {e.detail}")

            logger.info(f"POS: factura {comprobante_id} procesada en segundo plano")
    except Exception as e:
        logger.error(f"POS: error inesperado procesando factura {comprobante_id}: {e}")


# ==========================================
# Sesiones de Caja
# ==========================================

@router.post("/sessions", response_model=POSCashSessionResponse, status_code=status.HTTP_201_CREATED)
async def open_cash_session(
    data: POSCashSessionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Abrir una nueva sesión de caja"""
    data.warehouse_id = clean_uuid_param(data.warehouse_id, "warehouse_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    try:
        await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

        # Verificar que no haya otra sesión abierta para la misma caja
        existing = await db.execute(
            select(POSCashSession).where(
                POSCashSession.company_id == data.company_id,
                POSCashSession.numero_caja == data.numero_caja,
                POSCashSession.estado == CajaEstado.ABIERTA.value,
            )
        )
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una sesión abierta para la caja '{data.numero_caja}'.",
            )

        # Verificar almacén si se proporciona
        if data.warehouse_id:
            wh_result = await db.execute(
                select(Warehouse).where(
                    Warehouse.id == data.warehouse_id,
                    Warehouse.company_id == data.company_id,
                    Warehouse.is_active == True,
                )
            )
            if not wh_result.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Almacén no encontrado o no pertenece a la empresa.",
                )

        session = POSCashSession(
            company_id=data.company_id,
            warehouse_id=data.warehouse_id,
            numero_caja=data.numero_caja,
            user_id=current_user.id,
            estado=CajaEstado.ABIERTA.value,
            fecha_apertura=datetime.now(timezone.utc),
            monto_apertura=data.monto_apertura,
        )
        db.add(session)
        await db.flush()

        await log_action(
            db=db, user_id=current_user.id, user_email=current_user.email,
            action="CREATE", entity_type="pos_cash_session", entity_id=session.id,
            description=f"Sesión de caja abierta: {data.numero_caja} con USD {data.monto_apertura}",
            ip_address=request.client.host if request.client else None,
        )

        return POSCashSessionResponse.model_validate(session)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error opening POS session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al abrir la sesión de caja: {str(e)}",
        )


@router.get("/sessions", response_model=list[POSCashSessionResponse])
async def list_cash_sessions(
    company_id: str | None = None,
    estado: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar sesiones de caja"""
    company_id = clean_company_id(company_id)
    query = (
        select(POSCashSession)
        .join(Company, POSCashSession.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
    )

    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(POSCashSession.company_id == company_id)
    if estado:
        query = query.where(POSCashSession.estado == estado)

    query = query.order_by(POSCashSession.fecha_apertura.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    sessions = result.scalars().all()
    return [POSCashSessionResponse.model_validate(s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=POSCashSessionResponse)
async def get_cash_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una sesión de caja específica con sus tickets y arqueos"""
    session_id = validate_uuid(session_id, "session_id")
    result = await db.execute(
        select(POSCashSession).where(POSCashSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión de caja no encontrada.")
    await _get_company_for_user(db, session.company_id, effective_owner_id(current_user))
    return POSCashSessionResponse.model_validate(session)


@router.put("/sessions/{session_id}/close", response_model=POSCashSessionResponse)
async def close_cash_session(
    session_id: str,
    data: POSCashSessionClose,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cerrar una sesión de caja con arqueo final"""
    session_id = validate_uuid(session_id, "session_id")
    result = await db.execute(
        select(POSCashSession).where(POSCashSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión de caja no encontrada.")
    await _get_company_for_user(db, session.company_id, effective_owner_id(current_user))

    if session.estado != CajaEstado.ABIERTA.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La sesión de caja ya está cerrada.",
        )

    # Calcular monto de cierre
    monto_cierre_calculado = session.monto_apertura + session.total_ventas_efectivo - session.total_devoluciones
    monto_diferencia = data.monto_cierre_efectivo - monto_cierre_calculado

    # Crear arqueo final
    arqueo = POSArqueo(
        cash_session_id=session_id,
        company_id=session.company_id,
        tipo=ArqueoTipo.FINAL.value,
        total_efectivo_contado=data.monto_cierre_efectivo,
        total_efectivo_calculado=monto_cierre_calculado,
        diferencia=monto_diferencia,
        observaciones=data.observaciones_cierre,
        user_id=current_user.id,
    )
    db.add(arqueo)

    # Cerrar sesión
    session.estado = CajaEstado.CERRADA.value
    session.fecha_cierre = datetime.now(timezone.utc)
    session.monto_cierre_efectivo = data.monto_cierre_efectivo
    session.monto_cierre_calculado = monto_cierre_calculado
    session.monto_diferencia = monto_diferencia
    session.observaciones_cierre = data.observaciones_cierre

    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="pos_cash_session", entity_id=session.id,
        description=f"Sesión de caja cerrada: {session.numero_caja}. Diferencia: USD {monto_diferencia}",
        ip_address=request.client.host if request.client else None,
    )

    return POSCashSessionResponse.model_validate(session)


@router.post("/sessions/{session_id}/arqueo-parcial", response_model=POSArqueoResponse, status_code=status.HTTP_201_CREATED)
async def create_partial_arqueo(
    session_id: str,
    data: POSArqueoCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un arqueo parcial durante la sesión de caja"""
    session_id = validate_uuid(session_id, "session_id")
    result = await db.execute(
        select(POSCashSession).where(POSCashSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión de caja no encontrada.")
    await _get_company_for_user(db, session.company_id, effective_owner_id(current_user))

    if session.estado != CajaEstado.ABIERTA.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden hacer arqueos parciales en sesiones abiertas.",
        )

    # Calcular efectivo esperado
    total_efectivo_calculado = session.monto_apertura + session.total_ventas_efectivo - session.total_devoluciones
    diferencia = data.total_efectivo_contado - total_efectivo_calculado

    arqueo = POSArqueo(
        cash_session_id=session_id,
        company_id=session.company_id,
        tipo=ArqueoTipo.PARCIAL.value,
        billetes=json.dumps(data.billetes) if data.billetes else None,
        monedas=json.dumps(data.monedas) if data.monedas else None,
        total_billetes=data.total_billetes,
        total_monedas=data.total_monedas,
        total_efectivo_contado=data.total_efectivo_contado,
        total_efectivo_calculado=total_efectivo_calculado,
        diferencia=diferencia,
        observaciones=data.observaciones,
        user_id=current_user.id,
    )
    db.add(arqueo)
    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="CREATE", entity_type="pos_arqueo", entity_id=arqueo.id,
        description=f"Arqueo parcial en caja {session.numero_caja}. Diferencia: USD {diferencia}",
        ip_address=request.client.host if request.client else None,
    )

    return POSArqueoResponse.model_validate(arqueo)


@router.get("/sessions/{session_id}/resumen", response_model=POSCashSessionResumen)
async def get_cash_session_resumen(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener resumen de sesión de caja para arqueo"""
    session_id = validate_uuid(session_id, "session_id")
    result = await db.execute(
        select(POSCashSession).where(POSCashSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión de caja no encontrada.")
    await _get_company_for_user(db, session.company_id, effective_owner_id(current_user))

    # Contar tickets
    tickets_count = await db.execute(
        select(func.count(POSTicket.id)).where(POSTicket.cash_session_id == session_id)
    )
    cantidad_tickets = tickets_count.scalar() or 0

    paid_tickets_count = await db.execute(
        select(func.count(POSTicket.id)).where(
            POSTicket.cash_session_id == session_id,
            POSTicket.estado == TicketEstado.PAGADO.value,
        )
    )
    cantidad_tickets_pagados = paid_tickets_count.scalar() or 0

    # Calcular efectivo esperado
    efectivo_esperado = session.monto_apertura + session.total_ventas_efectivo - session.total_devoluciones

    return POSCashSessionResumen(
        id=session.id,
        numero_caja=session.numero_caja,
        estado=session.estado,
        fecha_apertura=session.fecha_apertura,
        monto_apertura=session.monto_apertura,
        total_ventas_efectivo=session.total_ventas_efectivo,
        total_ventas_tarjeta=session.total_ventas_tarjeta,
        total_ventas_credito=session.total_ventas_credito,
        total_ventas_otro=session.total_ventas_otro,
        total_ventas=session.total_ventas,
        total_propina=session.total_propina,
        total_descuentos=session.total_descuentos,
        total_devoluciones=session.total_devoluciones,
        efectivo_esperado=efectivo_esperado,
        cantidad_tickets=cantidad_tickets,
        cantidad_tickets_pagados=cantidad_tickets_pagados,
    )


# ==========================================
# Tickets POS
# ==========================================

@router.post("/tickets", response_model=POSTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: POSTicketCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crear un nuevo ticket de venta POS.
    Actualiza kardex (salida del almacén) y opcionalmente crea un comprobante.
    """
    data.cash_session_id = clean_uuid_param(data.cash_session_id, "cash_session_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # Verificar que la sesión de caja esté abierta
    session_result = await db.execute(
        select(POSCashSession).where(POSCashSession.id == data.cash_session_id)
    )
    session = session_result.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión de caja no encontrada.")
    if session.estado != CajaEstado.ABIERTA.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La sesión de caja está cerrada. No se pueden crear tickets.",
        )
    if session.company_id != data.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La sesión de caja no pertenece a la empresa indicada.",
        )

    # Validar tipo de venta
    if data.tipo_venta not in ("efectivo", "tarjeta", "credito", "mixto", "otro"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de venta inválido. Válidos: efectivo, tarjeta, credito, mixto, otro",
        )

    # Generar número de ticket
    numero_ticket = await _get_next_number(db, data.company_id, "TCK", POSTicket)

    # Calcular totales
    subtotal_sin_impuestos = Decimal("0")
    total_iva = Decimal("0")
    total_descuento = Decimal("0")

    detalles = []
    for det in data.detalles:
        # El descuento del POS se maneja como PORCENTAJE de la línea
        descuento_pct = det.descuento or Decimal("0")
        descuento_monto = (
            det.cantidad * det.precio_unitario * descuento_pct / Decimal("100")
        ).quantize(Decimal("0.01"))
        precio_total_sin_impuestos = (det.cantidad * det.precio_unitario - descuento_monto).quantize(Decimal("0.01"))
        iva_valor = (precio_total_sin_impuestos * det.iva_porcentaje / Decimal("100")).quantize(Decimal("0.01"))

        subtotal_sin_impuestos += precio_total_sin_impuestos
        total_iva += iva_valor
        total_descuento += descuento_monto

        detalles.append(POSTicketDetalle(
            product_id=det.product_id,
            codigo_principal=det.codigo_principal,
            descripcion=det.descripcion,
            cantidad=det.cantidad,
            unidad_medida=det.unidad_medida,
            precio_unitario=det.precio_unitario,
            descuento=descuento_monto,
            precio_total_sin_impuestos=precio_total_sin_impuestos,
            iva_codigo=det.iva_codigo,
            iva_porcentaje=det.iva_porcentaje,
            iva_valor=iva_valor,
        ))

    total_con_impuestos = subtotal_sin_impuestos + total_iva

    # Calcular cambio
    monto_total_pagado = data.monto_efectivo + data.monto_tarjeta + data.monto_credito + data.monto_otro
    cambio = monto_total_pagado - total_con_impuestos - data.propina
    if cambio < 0:
        cambio = Decimal("0")

    # Cliente defaults
    cliente_nombre = data.cliente_nombre or "CONSUMIDOR FINAL"
    cliente_identificacion = data.cliente_identificacion or "9999999999999"
    cliente_tipo_identificacion = data.cliente_tipo_identificacion or "07"

    # Crear ticket
    ticket = POSTicket(
        company_id=data.company_id,
        cash_session_id=data.cash_session_id,
        numero_ticket=numero_ticket,
        estado=TicketEstado.PAGADO.value,
        tipo_venta=data.tipo_venta,
        cliente_nombre=cliente_nombre,
        cliente_identificacion=cliente_identificacion,
        cliente_tipo_identificacion=cliente_tipo_identificacion,
        cliente_direccion=data.cliente_direccion,
        cliente_telefono=data.cliente_telefono,
        cliente_email=data.cliente_email,
        subtotal_sin_impuestos=subtotal_sin_impuestos,
        total_iva=total_iva,
        total_descuento=total_descuento,
        total_con_impuestos=total_con_impuestos,
        monto_efectivo=data.monto_efectivo,
        monto_tarjeta=data.monto_tarjeta,
        monto_credito=data.monto_credito,
        monto_otro=data.monto_otro,
        cambio=cambio,
        propina=data.propina,
        numero_tarjeta=data.numero_tarjeta,
        tarjeta_tipo=data.tarjeta_tipo,
        tarjeta_marca=data.tarjeta_marca,
        tarjeta_banco=data.tarjeta_banco,
        tarjeta_titular=data.tarjeta_titular,
        referencia_pago=data.referencia_pago,
        observaciones=data.observaciones,
        user_id=current_user.id,
        detalles=detalles,
    )
    db.add(ticket)
    await db.flush()

    # Generar factura electrónica (SRI) automáticamente si se solicitó
    comprobante = None
    if data.crear_comprobante:
        try:
            comprobante = await _crear_factura_desde_ticket(db, ticket, data, current_user)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"POS: error al generar factura del ticket {numero_ticket}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al generar la factura electrónica: {str(e)}",
            )

    # Actualizar totales de la sesión de caja
    if data.tipo_venta == "efectivo" or data.tipo_venta == "mixto":
        session.total_ventas_efectivo += data.monto_efectivo
    if data.tipo_venta == "tarjeta" or data.tipo_venta == "mixto":
        session.total_ventas_tarjeta += data.monto_tarjeta
    if data.tipo_venta == "credito":
        session.total_ventas_credito += data.monto_credito
    if data.tipo_venta == "otro":
        session.total_ventas_otro += data.monto_otro
    if data.tipo_venta == "mixto":
        session.total_ventas_credito += data.monto_credito
        session.total_ventas_otro += data.monto_otro

    session.total_ventas += total_con_impuestos
    session.total_propina += data.propina
    session.total_descuentos += total_descuento

    # Actualizar kardex (salida del almacén del POS)
    if session.warehouse_id:
        for det in detalles:
            # Obtener saldo actual
            last_saldo = await db.execute(
                select(Kardex)
                .where(
                    Kardex.product_id == det.product_id,
                    Kardex.company_id == data.company_id,
                    Kardex.warehouse_id == session.warehouse_id,
                    Kardex.is_active == True,
                )
                .order_by(Kardex.fecha_movimiento.desc(), Kardex.created_at.desc())
                .limit(1)
            )
            last_mov = last_saldo.scalars().first()
            saldo_cantidad = last_mov.saldo_cantidad if last_mov else Decimal("0")
            saldo_valor = last_mov.saldo_valor if last_mov else Decimal("0")

            # Calcular costo promedio
            costo_promedio = Decimal("0")
            if saldo_cantidad > 0:
                costo_promedio = saldo_valor / saldo_cantidad

            nuevo_saldo_cantidad = saldo_cantidad - det.cantidad
            nuevo_saldo_valor = saldo_valor - (det.cantidad * costo_promedio)

            if nuevo_saldo_cantidad < 0:
                nuevo_saldo_cantidad = Decimal("0")
                nuevo_saldo_valor = Decimal("0")

            costo_total_mov = det.cantidad * costo_promedio

            kardex_mov = Kardex(
                company_id=data.company_id,
                product_id=det.product_id,
                warehouse_id=session.warehouse_id,
                tipo_movimiento=KardexTipoMovimiento.SALIDA.value,
                cantidad=det.cantidad,
                costo_unitario=costo_promedio,
                costo_total=costo_total_mov,
                saldo_cantidad=nuevo_saldo_cantidad,
                saldo_valor=nuevo_saldo_valor,
                referencia_tipo="pos_ticket",
                referencia_id=ticket.id,
                referencia_secuencial=numero_ticket,
                detalle=f"Venta POS - Ticket {numero_ticket}",
                fecha_movimiento=datetime.now(timezone.utc),
                user_id=current_user.id,
            )
            db.add(kardex_mov)

            # Actualizar stock del producto
            if det.product_id:
                prod_result = await db.execute(
                    select(Product).where(Product.id == det.product_id)
                )
                product = prod_result.scalars().first()
                if product and hasattr(product, "stock"):
                    product.stock = nuevo_saldo_cantidad

    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="CREATE", entity_type="pos_ticket", entity_id=ticket.id,
        description=f"Ticket POS creado: {numero_ticket} por USD {total_con_impuestos}",
        ip_address=request.client.host if request.client else None,
    )

    # Procesar la factura electrónica en segundo plano (validar -> firmar -> SRI),
    # para no bloquear la venta en el POS mientras el SRI responde.
    if comprobante:
        # Las sub-cuentas firman con la firma de su cuenta principal
        firma_user_id = current_user.parent_user_id if current_user.is_subaccount else current_user.id
        background_tasks.add_task(
            _procesar_factura_pos,
            comprobante_id=str(comprobante.id),
            user_id=str(firma_user_id),
        )

    return POSTicketResponse.model_validate(ticket)


@router.get("/tickets", response_model=list[POSTicketResponse])
async def list_tickets(
    company_id: str | None = None,
    session_id: str | None = None,
    estado: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar tickets POS"""
    session_id = clean_uuid_param(session_id, "session_id")
    company_id = clean_company_id(company_id)
    query = (
        select(POSTicket)
        .join(Company, POSTicket.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
    )

    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(POSTicket.company_id == company_id)
    if session_id:
        query = query.where(POSTicket.cash_session_id == session_id)
    if estado:
        query = query.where(POSTicket.estado == estado)

    query = query.order_by(POSTicket.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    tickets = result.scalars().all()
    return [POSTicketResponse.model_validate(t) for t in tickets]


@router.get("/tickets/{ticket_id}", response_model=POSTicketResponse)
async def get_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un ticket POS específico con sus detalles"""
    ticket_id = validate_uuid(ticket_id, "ticket_id")
    result = await db.execute(
        select(POSTicket).where(POSTicket.id == ticket_id)
    )
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    await _get_company_for_user(db, ticket.company_id, effective_owner_id(current_user))
    return POSTicketResponse.model_validate(ticket)


@router.put("/tickets/{ticket_id}/anular", response_model=POSTicketResponse)
async def void_ticket(
    ticket_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Anular un ticket POS.
    Revierte kardex (entrada al almacén) y actualiza totales de la sesión.
    """
    ticket_id = validate_uuid(ticket_id, "ticket_id")
    result = await db.execute(
        select(POSTicket).where(POSTicket.id == ticket_id)
    )
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    await _get_company_for_user(db, ticket.company_id, effective_owner_id(current_user))

    if ticket.estado != TicketEstado.PAGADO.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden anular tickets en estado 'pagado'. Estado actual: '{ticket.estado}'.",
        )

    # Anular ticket
    ticket.estado = TicketEstado.ANULADO.value

    # Actualizar sesión de caja (revertir totales)
    session_result = await db.execute(
        select(POSCashSession).where(POSCashSession.id == ticket.cash_session_id)
    )
    session = session_result.scalars().first()
    if session:
        session.total_ventas_efectivo -= ticket.monto_efectivo
        session.total_ventas_tarjeta -= ticket.monto_tarjeta
        session.total_ventas_credito -= ticket.monto_credito
        session.total_ventas_otro -= ticket.monto_otro
        session.total_ventas -= ticket.total_con_impuestos
        session.total_propina -= ticket.propina
        session.total_descuentos -= ticket.total_descuento
        session.total_devoluciones += ticket.total_con_impuestos

    # Revertir kardex (entrada al almacén)
    if session and session.warehouse_id:
        for det in ticket.detalles:
            if det.product_id:
                # Obtener saldo actual
                last_saldo = await db.execute(
                    select(Kardex)
                    .where(
                        Kardex.product_id == det.product_id,
                        Kardex.company_id == ticket.company_id,
                        Kardex.warehouse_id == session.warehouse_id,
                        Kardex.is_active == True,
                    )
                    .order_by(Kardex.fecha_movimiento.desc(), Kardex.created_at.desc())
                    .limit(1)
                )
                last_mov = last_saldo.scalars().first()
                saldo_cantidad = last_mov.saldo_cantidad if last_mov else Decimal("0")
                saldo_valor = last_mov.saldo_valor if last_mov else Decimal("0")

                costo_promedio = Decimal("0")
                if saldo_cantidad > 0:
                    costo_promedio = saldo_valor / saldo_cantidad

                nuevo_saldo_cantidad = saldo_cantidad + det.cantidad
                costo_total_mov = det.cantidad * costo_promedio
                nuevo_saldo_valor = saldo_valor + costo_total_mov

                kardex_mov = Kardex(
                    company_id=ticket.company_id,
                    product_id=det.product_id,
                    warehouse_id=session.warehouse_id,
                    tipo_movimiento=KardexTipoMovimiento.ENTRADA.value,
                    cantidad=det.cantidad,
                    costo_unitario=costo_promedio,
                    costo_total=costo_total_mov,
                    saldo_cantidad=nuevo_saldo_cantidad,
                    saldo_valor=nuevo_saldo_valor,
                    referencia_tipo="pos_ticket_anulado",
                    referencia_id=ticket.id,
                    referencia_secuencial=ticket.numero_ticket,
                    detalle=f"Anulación de ticket POS - {ticket.numero_ticket}",
                    fecha_movimiento=datetime.now(timezone.utc),
                    user_id=current_user.id,
                )
                db.add(kardex_mov)

                # Actualizar stock del producto
                prod_result = await db.execute(
                    select(Product).where(Product.id == det.product_id)
                )
                product = prod_result.scalars().first()
                if product and hasattr(product, "stock"):
                    product.stock = nuevo_saldo_cantidad

    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="pos_ticket", entity_id=ticket.id,
        description=f"Ticket POS anulado: {ticket.numero_ticket}",
        ip_address=request.client.host if request.client else None,
    )

    return POSTicketResponse.model_validate(ticket)


@router.get("/tickets/{ticket_id}/print", response_model=POSTicketPrintResponse)
async def get_printable_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener datos de impresión de ticket (formato JSON para receipt)"""
    ticket_id = validate_uuid(ticket_id, "ticket_id")
    result = await db.execute(
        select(POSTicket).where(POSTicket.id == ticket_id)
    )
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    await _get_company_for_user(db, ticket.company_id, effective_owner_id(current_user))

    # Obtener datos de la empresa
    company_result = await db.execute(
        select(Company).where(Company.id == ticket.company_id)
    )
    company = company_result.scalars().first()

    # Obtener nombre del cajero
    user_result = await db.execute(
        select(User).where(User.id == ticket.user_id)
    )
    user = user_result.scalars().first()
    cajero_nombre = user.email if user else "N/A"

    # Obtener número de caja
    session_result = await db.execute(
        select(POSCashSession).where(POSCashSession.id == ticket.cash_session_id)
    )
    session = session_result.scalars().first()
    numero_caja = session.numero_caja if session else "N/A"

    # Preparar items
    items = []
    for det in ticket.detalles:
        items.append({
            "codigo": det.codigo_principal,
            "descripcion": det.descripcion,
            "cantidad": str(det.cantidad),
            "precio_unitario": str(det.precio_unitario),
            "descuento": str(det.descuento),
            "precio_total_sin_impuestos": str(det.precio_total_sin_impuestos),
            "iva_porcentaje": str(det.iva_porcentaje),
            "iva_valor": str(det.iva_valor),
        })

    return POSTicketPrintResponse(
        numero_ticket=ticket.numero_ticket,
        fecha=ticket.created_at,
        cliente_nombre=ticket.cliente_nombre,
        cliente_identificacion=ticket.cliente_identificacion,
        cliente_direccion=ticket.cliente_direccion,
        cliente_telefono=ticket.cliente_telefono,
        cliente_email=ticket.cliente_email,
        cajero=cajero_nombre,
        numero_caja=numero_caja,
        items=items,
        subtotal_sin_impuestos=ticket.subtotal_sin_impuestos,
        total_iva=ticket.total_iva,
        total_descuento=ticket.total_descuento,
        total_con_impuestos=ticket.total_con_impuestos,
        monto_efectivo=ticket.monto_efectivo,
        monto_tarjeta=ticket.monto_tarjeta,
        monto_credito=ticket.monto_credito,
        monto_otro=ticket.monto_otro,
        cambio=ticket.cambio,
        propina=ticket.propina,
        tipo_venta=ticket.tipo_venta,
        numero_tarjeta=ticket.numero_tarjeta,
        tarjeta_tipo=ticket.tarjeta_tipo,
        tarjeta_marca=ticket.tarjeta_marca,
        tarjeta_banco=ticket.tarjeta_banco,
        tarjeta_titular=ticket.tarjeta_titular,
        empresa_nombre=company.razon_social if company else None,
        empresa_ruc=company.ruc if company else None,
        empresa_direccion=company.dir_matriz if company else None,
    )


# ==========================================
# Ticket PDF (thermal 80mm receipt)
# ==========================================

@router.get("/tickets/{ticket_id}/pdf")
async def get_ticket_pdf(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generar PDF de ticket imprimible en formato termico 80mm.
    Retorna un StreamingResponse con el PDF listo para descargar/imprimir.
    """
    ticket_id = validate_uuid(ticket_id, "ticket_id")
    result = await db.execute(
        select(POSTicket).where(POSTicket.id == ticket_id)
    )
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket no encontrado.")
    await _get_company_for_user(db, ticket.company_id, effective_owner_id(current_user))

    # Obtener datos de la empresa
    company_result = await db.execute(
        select(Company).where(Company.id == ticket.company_id)
    )
    company = company_result.scalars().first()

    # Obtener nombre del cajero
    user_result = await db.execute(
        select(User).where(User.id == ticket.user_id)
    )
    user = user_result.scalars().first()
    cajero_nombre = user.email.split("@")[0] if user else "N/A"

    # Obtener numero de caja
    session_result = await db.execute(
        select(POSCashSession).where(POSCashSession.id == ticket.cash_session_id)
    )
    session = session_result.scalars().first()
    numero_caja = session.numero_caja if session else "N/A"

    # Configuracion PDF 80mm thermal
    paper_width = 80 * mm
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(paper_width, 500 * mm))
    c.setTitle(f"Ticket {ticket.numero_ticket}")

    # Margenes y ancho util
    margin = 3 * mm
    usable_width = paper_width - 2 * margin
    x = margin
    y = 480 * mm  # empezar desde arriba

    def draw_line(text: str, font_size: int = 7, bold: bool = False, align: str = "left") -> None:
        nonlocal y
        font_name = "Courier-Bold" if bold else "Courier"
        c.setFont(font_name, font_size)
        if align == "center":
            text_width = c.stringWidth(text, font_name, font_size)
            c.drawString((paper_width - text_width) / 2, y, text)
        elif align == "right":
            text_width = c.stringWidth(text, font_name, font_size)
            c.drawString(paper_width - margin - text_width, y, text)
        else:
            c.drawString(x, y, text)
        y -= font_size + 1.5

    def draw_separator(char: str = "-", font_size: int = 7) -> None:
        nonlocal y
        c.setFont("Courier", font_size)
        char_width = c.stringWidth(char, "Courier", font_size)
        if char_width > 0:
            num_chars = int(usable_width / char_width)
            c.drawString(x, y, char * num_chars)
        y -= font_size + 1.5

    def draw_two_lines(left: str, right: str, font_size: int = 7, bold: bool = False) -> None:
        nonlocal y
        font_name = "Courier-Bold" if bold else "Courier"
        c.setFont(font_name, font_size)
        left_width = c.stringWidth(left, font_name, font_size)
        right_width = c.stringWidth(right, font_name, font_size)
        c.drawString(x, y, left)
        c.drawString(paper_width - margin - right_width, y, right)
        y -= font_size + 1.5

    # --- Encabezado ---
    empresa_nombre = (company.razon_social if company else "EMPRESA").upper()
    draw_line(empresa_nombre, font_size=8, bold=True, align="center")
    if company and company.ruc:
        draw_line(f"RUC: {company.ruc}", font_size=7, align="center")
    if company and company.dir_matriz:
        dir_text = company.dir_matriz
        if len(dir_text) > 35:
            dir_text = dir_text[:32] + "..."
        draw_line(dir_text, font_size=6, align="center")

    draw_line("TICKET DE VENTA", font_size=8, bold=True, align="center")
    draw_separator()

    # --- Info del ticket ---
    draw_two_lines(f"Nro: {ticket.numero_ticket}", f"Caja: {numero_caja}")
    draw_two_lines(
        f"Fecha: {ticket.created_at.strftime('%d/%m/%Y %H:%M')}",
        f"Cajero: {cajero_nombre}",
        font_size=6,
    )
    draw_two_lines(f"Cliente: {ticket.cliente_nombre}", f"RUC/CI: {ticket.cliente_identificacion}")
    draw_separator()

    # --- Items ---
    draw_two_lines("CANT DESCRIPCION", "P.UNIT  SUBTOTAL", font_size=6, bold=True)
    draw_separator(char="~", font_size=6)

    for det in ticket.detalles:
        subtotal = det.precio_total_sin_impuestos
        desc_line = f"{det.cantidad:.4f} {det.descripcion[:20]}"
        price_line = f"{det.precio_unitario:.2f}  {subtotal:.2f}"
        draw_two_lines(desc_line, price_line, font_size=6)
        if det.descuento and det.descuento > 0:
            draw_line(f"  (Desc: {det.descuento:.2f})", font_size=6)
        if det.iva_porcentaje and det.iva_porcentaje > 0:
            draw_line(f"  IVA {det.iva_porcentaje}%: {det.iva_valor:.2f}", font_size=6)

    draw_separator()

    # --- Totales ---
    draw_two_lines("SUBTOTAL SIN IMPUESTOS:", f"{ticket.subtotal_sin_impuestos:.2f}", bold=True)
    draw_two_lines("TOTAL IVA:", f"{ticket.total_iva:.2f}")
    if ticket.total_descuento and ticket.total_descuento > 0:
        draw_two_lines("DESCUENTOS:", f"-{ticket.total_descuento:.2f}")
    draw_two_lines("TOTAL:", f"${ticket.total_con_impuestos:.2f}", font_size=9, bold=True)
    draw_separator()

    # --- Pago ---
    tipo_venta_label = {
        "efectivo": "EFECTIVO",
        "tarjeta": "TARJETA",
        "credito": "CREDITO",
        "mixto": "MIXTO",
        "otro": "OTRO",
    }.get(ticket.tipo_venta, ticket.tipo_venta.upper())

    draw_two_lines("Forma de pago:", tipo_venta_label)
    if ticket.monto_efectivo > 0:
        draw_two_lines("Efectivo recibido:", f"{ticket.monto_efectivo:.2f}")
    if ticket.monto_tarjeta > 0:
        draw_two_lines("Tarjeta:", f"{ticket.monto_tarjeta:.2f}")
    if ticket.cambio > 0:
        draw_two_lines("Cambio:", f"{ticket.cambio:.2f}", bold=True)
    if ticket.propina and ticket.propina > 0:
        draw_two_lines("Propina:", f"{ticket.propina:.2f}")

    draw_separator()
    draw_line("GRACIAS POR SU COMPRA", font_size=9, bold=True, align="center")
    draw_line("", font_size=4)  # espacio extra

    c.showPage()
    c.save()

    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ticket_{ticket.numero_ticket}.pdf"'},
    )


# ==========================================
# Arqueo de Caja - endpoints adicionales
# ==========================================

@router.post("/arqueos/{arqueo_id}/cerrar", response_model=POSArqueoCerrarResponse)
async def cerrar_arqueo(
    arqueo_id: str,
    data: POSArqueoCerrarRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cerrar un arqueo con desglose detallado de denominaciones.
    Calcula el efectivo real contado por billetes/monedas,
    compara con el esperado por el sistema, y flag diferencias.
    """
    arqueo_id = validate_uuid(arqueo_id, "arqueo_id")
    result = await db.execute(
        select(POSArqueo).where(POSArqueo.id == arqueo_id)
    )
    arqueo = result.scalars().first()
    if not arqueo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arqueo no encontrado.")

    # Verificar acceso a la empresa
    await _get_company_for_user(db, arqueo.company_id, effective_owner_id(current_user))

    # Obtener sesion de caja para contexto
    session_result = await db.execute(
        select(POSCashSession).where(POSCashSession.id == arqueo.cash_session_id)
    )
    session = session_result.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesion de caja no encontrada.")

    # --- Calcular total_efectivo_real desde desglose ---
    billetes_detalle = {
        "100": data.billetes_100,
        "50": data.billetes_50,
        "20": data.billetes_20,
        "10": data.billetes_10,
        "5": data.billetes_5,
        "1": data.billetes_1,
    }

    total_billetes = sum(
        Decimal(denom) * Decimal(cantidad)
        for denom, cantidad in billetes_detalle.items()
    )

    total_efectivo_real = total_billetes + data.monedas

    # --- Comparar con efectivo del sistema ---
    total_efectivo_sistema = arqueo.total_efectivo_calculado
    diferencia = total_efectivo_real - total_efectivo_sistema

    # --- Determinar estado de diferencia ---
    estado_diferencia = "OK"
    if abs(diferencia) > data.umbral_diferencia:
        estado_diferencia = "CON_DIFERENCIA"

    # --- Actualizar arqueo con nuevos datos ---
    arqueo.billetes = json.dumps(billetes_detalle)
    arqueo.monedas = json.dumps({"total": str(data.monedas)})
    arqueo.total_billetes = total_billetes
    arqueo.total_monedas = data.monedas
    arqueo.total_efectivo_contado = total_efectivo_real
    arqueo.total_efectivo_calculado = total_efectivo_sistema
    arqueo.diferencia = diferencia

    # Guardar campos adicionales como JSON en observaciones
    extras_info = {
        "vales": str(data.vales),
        "vouchers": str(data.vouchers),
        "estado_diferencia": estado_diferencia,
    }
    if arqueo.observaciones:
        extras_info["observaciones_originales"] = arqueo.observaciones
    if data.observaciones:
        extras_info["observaciones_cierre"] = data.observaciones
    arqueo.observaciones = json.dumps(extras_info, ensure_ascii=False)

    await db.flush()

    await log_action(
        db=db, user_id=current_user.id, user_email=current_user.email,
        action="UPDATE", entity_type="pos_arqueo", entity_id=arqueo.id,
        description=(
            f"Arqueo cerrado: {arqueo.tipo}. "
            f"Efectivo real: USD {total_efectivo_real}, "
            f"Sistema: USD {total_efectivo_sistema}, "
            f"Diferencia: USD {diferencia} ({estado_diferencia})"
        ),
        ip_address=request.client.host if request.client else None,
    )

    return POSArqueoCerrarResponse(
        id=arqueo.id,
        tipo=arqueo.tipo,
        total_efectivo_sistema=total_efectivo_sistema,
        total_efectivo_real=total_efectivo_real,
        diferencia=diferencia,
        estado_diferencia=estado_diferencia,
        detalle_billetes=billetes_detalle,
        total_monedas=data.monedas,
        total_vales=data.vales,
        total_vouchers=data.vouchers,
        observaciones=data.observaciones,
        created_at=arqueo.created_at,
    )


@router.get("/arqueos/resumen", response_model=POSArqueoResumenResponse)
async def get_arqueos_resumen(
    fecha_desde: datetime | None = Query(None, description="Fecha inicio (UTC)"),
    fecha_hasta: datetime | None = Query(None, description="Fecha fin (UTC)"),
    company_id: str | None = Query(None, description="ID de la empresa"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Resumen de todos los arqueos con filtro por rango de fechas.
    Incluye totales de sobrante/faltante y lista detallada.
    """
    company_id = clean_company_id(company_id)
    # Query base con join a sesion y company para filtrar por usuario
    query = (
        select(POSArqueo)
        .join(POSCashSession, POSArqueo.cash_session_id == POSCashSession.id)
        .join(Company, POSArqueo.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
    )

    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(POSArqueo.company_id == company_id)
    if fecha_desde:
        query = query.where(POSArqueo.created_at >= fecha_desde)
    if fecha_hasta:
        query = query.where(POSArqueo.created_at <= fecha_hasta)

    # Contar total registros
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total_registros = count_result.scalar() or 0

    # Obtener arqueos ordenados
    query = query.order_by(POSArqueo.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    arqueos = result.scalars().all()

    # Calcular totales y construir items
    total_sobrante = Decimal("0")
    total_faltante = Decimal("0")
    items = []

    for arqueo in arqueos:
        dif = arqueo.diferencia or Decimal("0")
        if dif > 0:
            total_sobrante += dif
        elif dif < 0:
            total_faltante += abs(dif)

        # Parsear estado_diferencia de observaciones si existe
        estado_diferencia = None
        if arqueo.observaciones:
            try:
                obs_data = json.loads(arqueo.observaciones)
                estado_diferencia = obs_data.get("estado_diferencia")
            except (json.JSONDecodeError, TypeError):
                pass

        # Obtener email del cajero
        user_result = await db.execute(
            select(User).where(User.id == arqueo.user_id)
        )
        cajero_user = user_result.scalars().first()
        cajero_email = cajero_user.email if cajero_user else "N/A"

        # Obtener numero de caja
        session_result = await db.execute(
            select(POSCashSession).where(POSCashSession.id == arqueo.cash_session_id)
        )
        sesion = session_result.scalars().first()
        numero_caja = sesion.numero_caja if sesion else "N/A"
        fecha_apertura = sesion.fecha_apertura if sesion else arqueo.created_at

        items.append(POSArqueoResumenItem(
            id=arqueo.id,
            numero_caja=numero_caja,
            tipo=arqueo.tipo,
            fecha_apertura=fecha_apertura,
            fecha_arqueo=arqueo.created_at,
            total_efectivo_sistema=arqueo.total_efectivo_calculado,
            total_efectivo_contado=arqueo.total_efectivo_contado,
            diferencia=dif,
            estado_diferencia=estado_diferencia,
            cajero_email=cajero_email,
        ))

    total_diferencia_neta = total_sobrante - total_faltante

    return POSArqueoResumenResponse(
        total_registros=total_registros,
        total_sobrante=total_sobrante,
        total_faltante=total_faltante,
        total_diferencia_neta=total_diferencia_neta,
        arqueos=items,
    )


@router.get("/arqueos/{arqueo_id}/reporte", response_model=POSArqueoReporteResponse)
async def get_arqueo_reporte(
    arqueo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener datos completos de un arqueo para generar reporte PDF.
    Incluye info de sesion, tickets, y desglose de efectivo.
    """
    arqueo_id = validate_uuid(arqueo_id, "arqueo_id")
    result = await db.execute(
        select(POSArqueo).where(POSArqueo.id == arqueo_id)
    )
    arqueo = result.scalars().first()
    if not arqueo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arqueo no encontrado.")
    await _get_company_for_user(db, arqueo.company_id, effective_owner_id(current_user))

    # Obtener sesion de caja
    session_result = await db.execute(
        select(POSCashSession).where(POSCashSession.id == arqueo.cash_session_id)
    )
    session = session_result.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesion de caja no encontrada.")

    # Obtener cajero
    user_result = await db.execute(
        select(User).where(User.id == arqueo.user_id)
    )
    cajero_user = user_result.scalars().first()
    cajero_nombre = cajero_user.email.split("@")[0] if cajero_user else "N/A"

    # Parsear billetes de JSON si existe
    detalle_billetes = None
    if arqueo.billetes:
        try:
            detalle_billetes = json.loads(arqueo.billetes)
        except (json.JSONDecodeError, TypeError):
            pass

    # Parsear estado_diferencia de observaciones
    estado_diferencia = None
    if arqueo.observaciones:
        try:
            obs_data = json.loads(arqueo.observaciones)
            estado_diferencia = obs_data.get("estado_diferencia")
        except (json.JSONDecodeError, TypeError):
            pass

    # Parsear vales/vouchers de observaciones
    total_vales = Decimal("0")
    total_vouchers = Decimal("0")
    if arqueo.observaciones:
        try:
            obs_data = json.loads(arqueo.observaciones)
            total_vales = Decimal(obs_data.get("vales", "0"))
            total_vouchers = Decimal(obs_data.get("vouchers", "0"))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    return POSArqueoReporteResponse(
        id=arqueo.id,
        tipo=arqueo.tipo,
        numero_caja=session.numero_caja,
        fecha_apertura=session.fecha_apertura,
        fecha_arqueo=arqueo.created_at,
        cajero=cajero_nombre,
        monto_apertura=session.monto_apertura,
        total_ventas_efectivo=session.total_ventas_efectivo,
        total_ventas_tarjeta=session.total_ventas_tarjeta,
        total_ventas_credito=session.total_ventas_credito,
        total_ventas=session.total_ventas,
        total_efectivo_sistema=arqueo.total_efectivo_calculado,
        detalle_billetes=detalle_billetes,
        total_monedas=arqueo.total_monedas or Decimal("0"),
        total_vales=total_vales,
        total_vouchers=total_vouchers,
        total_efectivo_real=arqueo.total_efectivo_contado,
        diferencia=arqueo.diferencia,
        estado_diferencia=estado_diferencia,
        observaciones=arqueo.observaciones,
    )


@router.get("/arqueos/{arqueo_id}/pdf")
async def get_arqueo_pdf(
    arqueo_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generar PDF de reporte de arqueo de caja.
    Formato carta con desglose detallado.
    """
    arqueo_id = validate_uuid(arqueo_id, "arqueo_id")
    # Obtener datos del arqueo
    result = await db.execute(
        select(POSArqueo).where(POSArqueo.id == arqueo_id)
    )
    arqueo = result.scalars().first()
    if not arqueo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arqueo no encontrado.")
    await _get_company_for_user(db, arqueo.company_id, effective_owner_id(current_user))

    # Obtener sesion y empresa
    session_result = await db.execute(
        select(POSCashSession).where(POSCashSession.id == arqueo.cash_session_id)
    )
    session = session_result.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesion de caja no encontrada.")

    company_result = await db.execute(
        select(Company).where(Company.id == arqueo.company_id)
    )
    company = company_result.scalars().first()

    user_result = await db.execute(
        select(User).where(User.id == arqueo.user_id)
    )
    cajero_user = user_result.scalars().first()
    cajero_nombre = cajero_user.email if cajero_user else "N/A"

    # Parsear datos
    detalle_billetes = {}
    if arqueo.billetes:
        try:
            detalle_billetes = json.loads(arqueo.billetes)
        except (json.JSONDecodeError, TypeError):
            pass

    estado_diferencia = None
    total_vales = Decimal("0")
    total_vouchers = Decimal("0")
    if arqueo.observaciones:
        try:
            obs_data = json.loads(arqueo.observaciones)
            estado_diferencia = obs_data.get("estado_diferencia")
            total_vales = Decimal(obs_data.get("vales", "0"))
            total_vouchers = Decimal(obs_data.get("vouchers", "0"))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    # Configuracion PDF carta
    from reportlab.lib.pagesizes import letter
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setTitle(f"Reporte Arqueo {arqueo.id}")

    width, height = letter
    margin = 40
    y = height - 50

    def draw_text(text: str, x: int = margin, font_size: int = 10, bold: bool = False) -> None:
        nonlocal y
        font_name = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font_name, font_size)
        c.drawString(x, y, text)
        y -= font_size + 4

    def draw_line_full(text: str, font_size: int = 10, bold: bool = False) -> None:
        draw_text(text, x=margin, font_size=font_size, bold=bold)

    def draw_two_col(left: str, right: str, font_size: int = 10, bold: bool = False) -> None:
        nonlocal y
        font_name = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font_name, font_size)
        c.drawString(margin, y, left)
        right_width = c.stringWidth(right, font_name, font_size)
        c.drawString(width - margin - right_width, y, right)
        y -= font_size + 4

    def draw_separator() -> None:
        nonlocal y
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.5)
        c.line(margin, y, width - margin, y)
        y -= 8

    # --- Encabezado ---
    empresa_nombre = company.razon_social if company else "EMPRESA"
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, y, "REPORTE DE ARQUEO DE CAJA")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, y, empresa_nombre)
    y -= 14
    if company and company.ruc:
        c.drawCentredString(width / 2, y, f"RUC: {company.ruc}")
        y -= 14
    draw_separator()

    # --- Info general ---
    draw_line_full("INFORMACION GENERAL", font_size=12, bold=True)
    draw_separator()
    draw_two_col("Numero de caja:", session.numero_caja)
    draw_two_col("Tipo de arqueo:", arqueo.tipo.upper())
    draw_two_col("Fecha apertura:", session.fecha_apertura.strftime("%d/%m/%Y %H:%M"))
    draw_two_col("Fecha arqueo:", arqueo.created_at.strftime("%d/%m/%Y %H:%M"))
    draw_two_col("Cajero:", cajero_nombre)
    y -= 4

    # --- Resumen de ventas ---
    draw_line_full("RESUMEN DE VENTAS", font_size=12, bold=True)
    draw_separator()
    draw_two_col("Ventas en efectivo:", f"$ {session.total_ventas_efectivo:.2f}")
    draw_two_col("Ventas con tarjeta:", f"$ {session.total_ventas_tarjeta:.2f}")
    draw_two_col("Ventas a credito:", f"$ {session.total_ventas_credito:.2f}")
    draw_two_col("Total ventas:", f"$ {session.total_ventas:.2f}", bold=True)
    draw_two_col("Monto apertura:", f"$ {session.monto_apertura:.2f}")
    y -= 4

    # --- Efectivo esperado vs real ---
    draw_line_full("CONTEO DE EFECTIVO", font_size=12, bold=True)
    draw_separator()
    draw_two_col("Efectivo esperado (sistema):", f"$ {arqueo.total_efectivo_calculado:.2f}", bold=True)
    y -= 4

    # Billetes
    draw_line_full("Desglose de billetes:", font_size=10, bold=True)
    for denom in ["100", "50", "20", "10", "5", "1"]:
        cantidad = detalle_billetes.get(denom, 0)
        subtotal = Decimal(denom) * cantidad
        if cantidad > 0:
            draw_text(f"  Billetes ${denom}: {cantidad} = ${subtotal:.2f}", font_size=9)
    draw_text(f"  Total billetes: $ {arqueo.total_billetes:.2f}", font_size=10, bold=True)
    y -= 4

    draw_two_col("Total monedas:", f"$ {arqueo.total_monedas:.2f}")
    draw_two_col("Total vales:", f"$ {total_vales:.2f}")
    draw_two_col("Total vouchers/tarjetas:", f"$ {total_vouchers:.2f}")
    draw_separator()
    draw_two_col("TOTAL EFECTIVO REAL:", f"$ {arqueo.total_efectivo_contado:.2f}", bold=True)
    y -= 4

    # --- Diferencia ---
    draw_line_full("DIFERENCIA", font_size=12, bold=True)
    draw_separator()
    dif = arqueo.diferencia
    dif_str = f"+${dif:.2f}" if dif >= 0 else f"-${abs(dif):.2f}"
    draw_two_col("Diferencia:", dif_str, bold=True)
    if estado_diferencia:
        estado_text = "CON DIFERENCIA" if estado_diferencia == "CON_DIFERENCIA" else "OK"
        c.setFont("Helvetica-Bold", 14)
        if estado_diferencia == "CON_DIFERENCIA":
            c.setFillColorRGB(0.8, 0, 0)
        else:
            c.setFillColorRGB(0, 0.6, 0)
        c.drawCentredString(width / 2, y - 10, estado_text)
        c.setFillColorRGB(0, 0, 0)
        y -= 28

    # --- Observaciones ---
    if arqueo.observaciones:
        draw_separator()
        draw_line_full("OBSERVACIONES", font_size=12, bold=True)
        try:
            obs_data = json.loads(arqueo.observaciones)
            obs_text = obs_data.get("observaciones_cierre", "")
            if not obs_text:
                obs_text = obs_data.get("observaciones_originales", "")
        except (json.JSONDecodeError, TypeError):
            obs_text = arqueo.observaciones
        if obs_text:
            words = obs_text.split()
            lines = []
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if len(test_line) <= 70:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            for line in lines:
                draw_text(line, font_size=9)

    c.showPage()
    c.save()

    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="arqueo_{arqueo_id}.pdf"'},
    )


# ==========================================
# Busqueda de producto por codigo de barras
# ==========================================

@router.get("/products/search", response_model=list[POSProductSearchResponse])
async def search_products(
    q: str = Query("", description="Texto de búsqueda: código de barras, código principal o nombre"),
    barcode: str | None = Query(None, description="Alias de búsqueda por código de barras exacto"),
    company_id: str = Query(..., description="ID de la empresa"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Buscar productos para el POS.

    - Si `q` coincide exactamente con un código de barras, devuelve ese producto.
    - Si no, busca por código principal o descripción (coincidencia parcial).
    - Con `q` vacío devuelve todos los productos activos de la empresa.
    """
    company_id = validate_uuid(company_id, "company_id")
    await _get_company_for_user(db, company_id, effective_owner_id(current_user))

    query = select(Product).where(
        Product.company_id == company_id,
        Product.is_active == True,  # noqa: E712
    )

    q = (q or "").strip()
    if not q and barcode:
        q = str(barcode).strip()
    if q:
        # Coincidencia exacta de código de barras primero
        query = query.where(
            (Product.codigo_barras == q)
            | (Product.codigo_principal.ilike(f"%{q}%"))
            | (Product.descripcion.ilike(f"%{q}%"))
        )

    query = query.order_by(Product.descripcion).limit(50)
    result = await db.execute(query)
    products = result.scalars().all()

    return [
        POSProductSearchResponse(
            id=p.id,
            codigo_principal=p.codigo_principal,
            codigo_barras=p.codigo_barras,
            descripcion=p.descripcion,
            tipo=p.tipo,
            precio_unitario=p.precio_unitario,
            iva_codigo=p.iva_codigo,
            iva_porcentaje=p.iva_porcentaje,
            unidad_medida=p.unidad_medida,
            stock=p.stock,
            stock_minimo=p.stock_minimo,
        )
        for p in products
    ]


@router.post("/tickets/search-barcode", response_model=POSProductSearchResponse)
async def search_product_by_barcode(
    barcode: str = Query(..., description="Código de barras a buscar"),
    company_id: str = Query(..., description="ID de la empresa"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Buscar producto por código de barras para POS"""
    company_id = validate_uuid(company_id, "company_id")
    await _get_company_for_user(db, company_id, effective_owner_id(current_user))

    result = await db.execute(
        select(Product).where(
            Product.company_id == company_id,
            Product.codigo_barras == barcode,
            Product.is_active == True,
        )
    )
    product = result.scalars().first()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Producto con código de barras '{barcode}' no encontrado.",
        )

    return POSProductSearchResponse(
        id=product.id,
        codigo_principal=product.codigo_principal,
        codigo_barras=product.codigo_barras,
        descripcion=product.descripcion,
        tipo=product.tipo,
        precio_unitario=product.precio_unitario,
        iva_codigo=product.iva_codigo,
        iva_porcentaje=product.iva_porcentaje,
        unidad_medida=product.unidad_medida,
        stock=product.stock,
        stock_minimo=product.stock_minimo,
    )

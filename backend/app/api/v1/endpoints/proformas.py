"""
ContaEC - Endpoints de Proformas
CRUD de proformas, envío, conversión a factura
"""
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.core.xml_generator import generate_clave_acceso
from app.models.client import Client
from app.models.company import Company
from app.models.comprobante import Comprobante, ComprobanteDetalle, ComprobanteEstado
from app.models.proforma import Proforma, ProformaDetalle, ProformaEstado
from app.models.user import User
from app.schemas.comprobante import ComprobanteCreate, ComprobanteResponse
from app.schemas.proforma import (
    ProformaCreate,
    ProformaListResponse,
    ProformaResponse,
    ProformaStatsResponse,
    ProformaUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/proformas", tags=["Proformas"])


# ==========================================
# Funciones auxiliares
# ==========================================

async def _get_company_for_user(
    db: AsyncSession,
    company_id: str,
    user_id: str,
) -> Company:
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


def _calcular_totales_proforma(detalles: list) -> dict:
    """Calcula los totales de la proforma a partir de los detalles"""
    subtotal_sin_impuestos = Decimal("0")
    total_iva = Decimal("0")
    total_ice = Decimal("0")
    total_descuento = Decimal("0")

    subtotal_iva_0 = Decimal("0")
    subtotal_iva_5 = Decimal("0")
    subtotal_iva_8 = Decimal("0")
    subtotal_iva_12 = Decimal("0")
    subtotal_iva_13 = Decimal("0")
    subtotal_iva_14 = Decimal("0")
    subtotal_iva_15 = Decimal("0")
    subtotal_no_objeto_iva = Decimal("0")
    subtotal_exento_iva = Decimal("0")

    detalle_resultados = []

    for det in detalles:
        # Descuento efectivo según su tipo:
        # - 'porcentaje': % del total de la línea (cantidad * precio_unitario)
        # - 'dolares': monto fijo
        if getattr(det, "descuento_tipo", None) == "porcentaje" and getattr(det, "descuento_valor", None):
            descuento_monto = (
                det.cantidad * det.precio_unitario * det.descuento_valor / Decimal("100")
            ).quantize(Decimal("0.01"))
        elif getattr(det, "descuento_tipo", None) == "dolares" and getattr(det, "descuento_valor", None):
            descuento_monto = Decimal(det.descuento_valor).quantize(Decimal("0.01"))
        else:
            descuento_monto = det.descuento or Decimal("0")

        precio_total = det.cantidad * det.precio_unitario - descuento_monto
        precio_total = precio_total.quantize(Decimal("0.01"))

        iva_valor = (precio_total * (det.iva_porcentaje / 100)).quantize(Decimal("0.01"))

        ice_valor = Decimal("0")
        if det.ice_porcentaje:
            ice_valor = (precio_total * (det.ice_porcentaje / 100)).quantize(Decimal("0.01"))

        subtotal_sin_impuestos += precio_total
        total_iva += iva_valor
        total_ice += ice_valor
        total_descuento += descuento_monto

        porc = det.iva_porcentaje
        if porc == Decimal("0"):
            if det.iva_codigo == "6":
                subtotal_no_objeto_iva += precio_total
            elif det.iva_codigo == "7":
                subtotal_exento_iva += precio_total
            else:
                subtotal_iva_0 += precio_total
        elif porc == Decimal("5"):
            subtotal_iva_5 += precio_total
        elif porc == Decimal("8"):
            subtotal_iva_8 += precio_total
        elif porc == Decimal("12"):
            subtotal_iva_12 += precio_total
        elif porc == Decimal("13"):
            subtotal_iva_13 += precio_total
        elif porc == Decimal("14"):
            subtotal_iva_14 += precio_total
        elif porc == Decimal("15"):
            subtotal_iva_15 += precio_total
        else:
            subtotal_iva_0 += precio_total

        detalle_resultados.append({
            "precio_total_sin_impuestos": precio_total,
            "iva_valor": iva_valor,
            "ice_valor": ice_valor,
            "descuento": descuento_monto,
        })

    total_con_impuestos = (subtotal_sin_impuestos + total_iva + total_ice).quantize(Decimal("0.01"))

    return {
        "subtotal_sin_impuestos": subtotal_sin_impuestos.quantize(Decimal("0.01")),
        "total_iva": total_iva.quantize(Decimal("0.01")),
        "total_ice": total_ice.quantize(Decimal("0.01")),
        "total_descuento": total_descuento.quantize(Decimal("0.01")),
        "total_con_impuestos": total_con_impuestos,
        "subtotal_iva_0": subtotal_iva_0.quantize(Decimal("0.01")),
        "subtotal_iva_5": subtotal_iva_5.quantize(Decimal("0.01")),
        "subtotal_iva_8": subtotal_iva_8.quantize(Decimal("0.01")),
        "subtotal_iva_12": subtotal_iva_12.quantize(Decimal("0.01")),
        "subtotal_iva_13": subtotal_iva_13.quantize(Decimal("0.01")),
        "subtotal_iva_14": subtotal_iva_14.quantize(Decimal("0.01")),
        "subtotal_iva_15": subtotal_iva_15.quantize(Decimal("0.01")),
        "subtotal_no_objeto_iva": subtotal_no_objeto_iva.quantize(Decimal("0.01")),
        "subtotal_exento_iva": subtotal_exento_iva.quantize(Decimal("0.01")),
        "detalle_resultados": detalle_resultados,
    }


# ==========================================
# Endpoints
# ==========================================

@router.post("", response_model=ProformaResponse, status_code=status.HTTP_201_CREATED)
async def create_proforma(
    data: ProformaCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva proforma"""
    data.client_id = clean_uuid_param(data.client_id, "client_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    try:
        company = await _get_company_for_user(db, data.company_id, current_user.id)

        # Client info
        cliente_tipo_identificacion = "07"
        cliente_identificacion = "9999999999999"
        cliente_razon_social = "CONSUMIDOR FINAL"
        cliente_direccion = None
        cliente_email = None
        cliente_telefono = None

        if data.client_id:
            result = await db.execute(
                select(Client).where(
                    Client.id == data.client_id,
                    Client.company_id == data.company_id,
                    Client.is_active == True,
                )
            )
            client = result.scalars().first()
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente no encontrado o no pertenece a la empresa.",
                )
            cliente_tipo_identificacion = client.tipo_identificacion
            cliente_identificacion = client.identificacion
            cliente_razon_social = client.razon_social
            cliente_direccion = client.direccion
            cliente_email = client.email
            cliente_telefono = client.telefono

        # Calculate totals
        totales = _calcular_totales_proforma(data.detalles)

        # Get sequential
        secuencial = company.get_next_secuencial_proforma()

        # Parse fecha_validez
        fecha_validez = None
        if data.fecha_validez:
            try:
                fecha_validez = datetime.fromisoformat(data.fecha_validez).replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        proforma = Proforma(
            company_id=data.company_id,
            client_id=data.client_id,
            user_id=current_user.id,
            secuencial=secuencial,
            fecha_emision=datetime.now(timezone.utc),
            fecha_validez=fecha_validez,
            estado=ProformaEstado.BORRADOR,
            cliente_tipo_identificacion=cliente_tipo_identificacion,
            cliente_identificacion=cliente_identificacion,
            cliente_razon_social=cliente_razon_social,
            cliente_direccion=cliente_direccion,
            cliente_email=cliente_email,
            cliente_telefono=cliente_telefono,
            subtotal_sin_impuestos=totales["subtotal_sin_impuestos"],
            subtotal_iva_0=totales["subtotal_iva_0"],
            subtotal_iva_5=totales["subtotal_iva_5"],
            subtotal_iva_8=totales["subtotal_iva_8"],
            subtotal_iva_12=totales["subtotal_iva_12"],
            subtotal_iva_13=totales["subtotal_iva_13"],
            subtotal_iva_14=totales["subtotal_iva_14"],
            subtotal_iva_15=totales["subtotal_iva_15"],
            subtotal_no_objeto_iva=totales["subtotal_no_objeto_iva"],
            subtotal_exento_iva=totales["subtotal_exento_iva"],
            total_iva=totales["total_iva"],
            total_ice=totales["total_ice"],
            total_descuento=totales["total_descuento"],
            total_con_impuestos=totales["total_con_impuestos"],
            forma_pago=data.forma_pago,
            observaciones=data.observaciones,
            info_adicional=json.dumps(data.info_adicional) if data.info_adicional else None,
        )
        db.add(proforma)
        await db.flush()

        for i, det_data in enumerate(data.detalles):
            det_result = totales["detalle_resultados"][i]
            detalle = ProformaDetalle(
                proforma_id=proforma.id,
                product_id=det_data.product_id,
                codigo_principal=det_data.codigo_principal,
                codigo_auxiliar=det_data.codigo_auxiliar,
                descripcion=det_data.descripcion,
                cantidad=det_data.cantidad,
                unidad_medida=det_data.unidad_medida,
                precio_unitario=det_data.precio_unitario,
                descuento=det_result["descuento"],
                precio_total_sin_impuestos=det_result["precio_total_sin_impuestos"],
                iva_codigo=det_data.iva_codigo,
                iva_porcentaje=det_data.iva_porcentaje,
                iva_valor=det_result["iva_valor"],
                ice_codigo=det_data.ice_codigo,
                ice_porcentaje=det_data.ice_porcentaje,
                ice_valor=det_result["ice_valor"],
            )
            db.add(detalle)

        await db.flush()

        logger.info(f"Proforma creada: secuencial={secuencial}, empresa={company.ruc}")

        # Recargar con los detalles cargados explícitamente (evita lazy-load en async:
        # MissingGreenlet: greenlet_spawn has not been called)
        from sqlalchemy.orm import selectinload

        result = await db.execute(
            select(Proforma)
            .options(selectinload(Proforma.detalles))
            .where(Proforma.id == proforma.id)
        )
        proforma = result.scalars().first()

        return ProformaResponse.model_validate(proforma)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating proforma: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al crear la proforma: {str(e)}",
        )


@router.get("", response_model=list[ProformaListResponse])
async def list_proformas(
    company_id: str | None = None,
    estado: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar proformas del usuario"""
    company_id = clean_company_id(company_id)
    query = (
        select(Proforma)
        .join(Company, Proforma.company_id == Company.id)
        .where(Company.user_id == current_user.id)
        .where(Proforma.is_active == True)
        .order_by(Proforma.fecha_emision.desc())
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(Proforma.company_id == company_id)

    if estado:
        query = query.where(Proforma.estado == estado)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    proformas = result.scalars().all()

    return [ProformaListResponse.model_validate(p) for p in proformas]


@router.get("/stats", response_model=ProformaStatsResponse)
async def get_proforma_stats(
    company_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener estadísticas de proformas"""
    company_id = clean_company_id(company_id)
    base_query = (
        select(Proforma)
        .join(Company, Proforma.company_id == Company.id)
        .where(Company.user_id == current_user.id)
        .where(Proforma.is_active == True)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        base_query = base_query.where(Proforma.company_id == company_id)

    result = await db.execute(base_query)
    proformas = result.scalars().all()

    stats = {
        "total": len(proformas),
        "borrador": 0,
        "enviada": 0,
        "aceptada": 0,
        "rechazada": 0,
        "convertida": 0,
    }

    for p in proformas:
        estado = p.estado
        if estado == ProformaEstado.BORRADOR:
            stats["borrador"] += 1
        elif estado == ProformaEstado.ENVIADA:
            stats["enviada"] += 1
        elif estado == ProformaEstado.ACEPTADA:
            stats["aceptada"] += 1
        elif estado == ProformaEstado.RECHAZADA:
            stats["rechazada"] += 1
        elif estado == ProformaEstado.CONVERTIDA:
            stats["convertida"] += 1

    return ProformaStatsResponse(**stats)


@router.get("/{proforma_id}", response_model=ProformaResponse)
async def get_proforma(
    proforma_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una proforma específica"""
    proforma_id = validate_uuid(proforma_id, "proforma_id")
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Proforma)
        .options(selectinload(Proforma.detalles))
        .where(
            Proforma.id == proforma_id,
            Proforma.is_active == True,
        )
    )
    proforma = result.scalars().first()

    if not proforma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proforma no encontrada.",
        )

    await _get_company_for_user(db, proforma.company_id, current_user.id)

    return ProformaResponse.model_validate(proforma)


@router.put("/{proforma_id}", response_model=ProformaResponse)
async def update_proforma(
    proforma_id: str,
    data: ProformaUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una proforma (solo BORRADOR)"""
    data.client_id = clean_uuid_param(data.client_id, "client_id")
    proforma_id = validate_uuid(proforma_id, "proforma_id")
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Proforma)
        .options(selectinload(Proforma.detalles))
        .where(
            Proforma.id == proforma_id,
            Proforma.is_active == True,
        )
    )
    proforma = result.scalars().first()

    if not proforma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proforma no encontrada.",
        )

    await _get_company_for_user(db, proforma.company_id, current_user.id)

    if proforma.estado != ProformaEstado.BORRADOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden editar proformas en estado BORRADOR.",
        )

    # Update client if provided
    if data.client_id is not None:
        if data.client_id:
            client_result = await db.execute(
                select(Client).where(
                    Client.id == data.client_id,
                    Client.company_id == proforma.company_id,
                    Client.is_active == True,
                )
            )
            client = client_result.scalars().first()
            if not client:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cliente no encontrado.",
                )
            proforma.client_id = data.client_id
            proforma.cliente_tipo_identificacion = client.tipo_identificacion
            proforma.cliente_identificacion = client.identificacion
            proforma.cliente_razon_social = client.razon_social
            proforma.cliente_direccion = client.direccion
            proforma.cliente_email = client.email
            proforma.cliente_telefono = client.telefono
        else:
            proforma.client_id = None
            proforma.cliente_tipo_identificacion = "07"
            proforma.cliente_identificacion = "9999999999999"
            proforma.cliente_razon_social = "CONSUMIDOR FINAL"
            proforma.cliente_direccion = None
            proforma.cliente_email = None
            proforma.cliente_telefono = None

    # Update detalles if provided
    if data.detalles is not None:
        # Eliminar detalles existentes (cascade delete-orphan actualiza la colección en memoria)
        proforma.detalles.clear()
        await db.flush()

        totales = _calcular_totales_proforma(data.detalles)

        proforma.subtotal_sin_impuestos = totales["subtotal_sin_impuestos"]
        proforma.subtotal_iva_0 = totales["subtotal_iva_0"]
        proforma.subtotal_iva_5 = totales["subtotal_iva_5"]
        proforma.subtotal_iva_8 = totales["subtotal_iva_8"]
        proforma.subtotal_iva_12 = totales["subtotal_iva_12"]
        proforma.subtotal_iva_13 = totales["subtotal_iva_13"]
        proforma.subtotal_iva_14 = totales["subtotal_iva_14"]
        proforma.subtotal_iva_15 = totales["subtotal_iva_15"]
        proforma.subtotal_no_objeto_iva = totales["subtotal_no_objeto_iva"]
        proforma.subtotal_exento_iva = totales["subtotal_exento_iva"]
        proforma.total_iva = totales["total_iva"]
        proforma.total_ice = totales["total_ice"]
        proforma.total_descuento = totales["total_descuento"]
        proforma.total_con_impuestos = totales["total_con_impuestos"]

        for i, det_data in enumerate(data.detalles):
            det_result = totales["detalle_resultados"][i]
            detalle = ProformaDetalle(
                proforma_id=proforma.id,
                product_id=det_data.product_id,
                codigo_principal=det_data.codigo_principal,
                codigo_auxiliar=det_data.codigo_auxiliar,
                descripcion=det_data.descripcion,
                cantidad=det_data.cantidad,
                unidad_medida=det_data.unidad_medida,
                precio_unitario=det_data.precio_unitario,
                descuento=det_result["descuento"],
                precio_total_sin_impuestos=det_result["precio_total_sin_impuestos"],
                iva_codigo=det_data.iva_codigo,
                iva_porcentaje=det_data.iva_porcentaje,
                iva_valor=det_result["iva_valor"],
                ice_codigo=det_data.ice_codigo,
                ice_porcentaje=det_data.ice_porcentaje,
                ice_valor=det_result["ice_valor"],
            )
            db.add(detalle)
            # Poblar la relación en memoria para evitar lazy-load (MissingGreenlet)
            proforma.detalles.append(detalle)

    if data.observaciones is not None:
        proforma.observaciones = data.observaciones
    if data.forma_pago is not None:
        proforma.forma_pago = data.forma_pago
    if data.fecha_validez is not None:
        try:
            proforma.fecha_validez = datetime.fromisoformat(data.fecha_validez).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    if data.info_adicional is not None:
        proforma.info_adicional = json.dumps(data.info_adicional)

    await db.flush()

    return ProformaResponse.model_validate(proforma)


@router.delete("/{proforma_id}")
async def delete_proforma(
    proforma_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar lógicamente una proforma (solo BORRADOR)"""
    proforma_id = validate_uuid(proforma_id, "proforma_id")
    result = await db.execute(
        select(Proforma).where(
            Proforma.id == proforma_id,
            Proforma.is_active == True,
        )
    )
    proforma = result.scalars().first()

    if not proforma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proforma no encontrada.",
        )

    await _get_company_for_user(db, proforma.company_id, current_user.id)

    if proforma.estado != ProformaEstado.BORRADOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar proformas en estado BORRADOR.",
        )

    proforma.is_active = False
    await db.flush()

    return {"message": "Proforma eliminada exitosamente."}


@router.post("/{proforma_id}/enviar")
async def enviar_proforma(
    proforma_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marcar proforma como ENVIADA"""
    proforma_id = validate_uuid(proforma_id, "proforma_id")
    result = await db.execute(
        select(Proforma).where(
            Proforma.id == proforma_id,
            Proforma.is_active == True,
        )
    )
    proforma = result.scalars().first()

    if not proforma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proforma no encontrada.",
        )

    await _get_company_for_user(db, proforma.company_id, current_user.id)

    if proforma.estado != ProformaEstado.BORRADOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La proforma debe estar en estado BORRADOR para enviarla. Estado actual: {proforma.estado}",
        )

    proforma.estado = ProformaEstado.ENVIADA
    await db.flush()

    return {
        "message": "Proforma marcada como enviada.",
        "estado": proforma.estado,
    }


@router.post("/{proforma_id}/convertir")
async def convertir_proforma(
    proforma_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Convertir una proforma en Factura electrónica (Comprobante tipo 01)"""
    proforma_id = validate_uuid(proforma_id, "proforma_id")
    result = await db.execute(
        select(Proforma).where(
            Proforma.id == proforma_id,
            Proforma.is_active == True,
        )
    )
    proforma = result.scalars().first()

    if not proforma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proforma no encontrada.",
        )

    company = await _get_company_for_user(db, proforma.company_id, current_user.id)

    if proforma.estado not in (ProformaEstado.ENVIADA, ProformaEstado.ACEPTADA):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La proforma debe estar en estado ENVIADA o ACEPTADA para convertirla.",
        )

    if proforma.comprobante_convertido_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta proforma ya fue convertida a factura.",
        )

    # Ensure client exists (proformas without client use Consumidor Final)
    # Find or create a default consumer client for this company
    client_result = await db.execute(
        select(Client).where(
            Client.company_id == company.id,
            Client.is_default_consumer == True,
            Client.is_active == True,
        )
    )
    client = client_result.scalars().first()

    if not client:
        # Create default consumer
        client = Client(
            company_id=company.id,
            tipo_identificacion="07",
            identificacion="9999999999999",
            razon_social="CONSUMIDOR FINAL",
            is_default_consumer=True,
        )
        db.add(client)
        await db.flush()

    # Get secuencial for factura
    secuencial = company.get_next_secuencial("01")

    # Generate clave de acceso
    fecha_emision = datetime.now(timezone.utc)
    try:
        clave_acceso = generate_clave_acceso(
            fecha_emision=fecha_emision.date(),
            tipo_comprobante="01",
            ruc=company.ruc,
            ambiente=company.tipo_ambiente,
            establecimiento=company.cod_establecimiento,
            punto_emision=company.cod_punto_emision,
            secuencial=secuencial,
            tipo_emision=company.tipo_emision,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al generar clave de acceso: {str(e)}",
        )

    # Create Comprobante from proforma data
    comprobante = Comprobante(
        company_id=company.id,
        client_id=client.id,
        user_id=current_user.id,
        tipo_comprobante="01",
        secuencial=secuencial,
        fecha_emision=fecha_emision,
        clave_acceso=clave_acceso,
        estado=ComprobanteEstado.BORRADOR,
        ambiente=company.tipo_ambiente,
        tipo_emision=company.tipo_emision,
        cliente_tipo_identificacion=proforma.cliente_tipo_identificacion,
        cliente_identificacion=proforma.cliente_identificacion,
        cliente_razon_social=proforma.cliente_razon_social,
        cliente_direccion=proforma.cliente_direccion,
        cliente_email=proforma.cliente_email,
        cliente_telefono=proforma.cliente_telefono,
        subtotal_sin_impuestos=proforma.subtotal_sin_impuestos,
        subtotal_iva_0=proforma.subtotal_iva_0,
        subtotal_iva_5=proforma.subtotal_iva_5,
        subtotal_iva_8=proforma.subtotal_iva_8,
        subtotal_iva_12=proforma.subtotal_iva_12,
        subtotal_iva_13=proforma.subtotal_iva_13,
        subtotal_iva_14=proforma.subtotal_iva_14,
        subtotal_iva_15=proforma.subtotal_iva_15,
        subtotal_no_objeto_iva=proforma.subtotal_no_objeto_iva,
        subtotal_exento_iva=proforma.subtotal_exento_iva,
        total_iva=proforma.total_iva,
        total_ice=proforma.total_ice,
        total_descuento=proforma.total_descuento,
        total_con_impuestos=proforma.total_con_impuestos,
        forma_pago=proforma.forma_pago or "01",
        info_adicional=proforma.info_adicional,
    )
    db.add(comprobante)
    await db.flush()

    # Copy detalles
    for prof_det in proforma.detalles:
        comp_det = ComprobanteDetalle(
            comprobante_id=comprobante.id,
            product_id=prof_det.product_id,
            codigo_principal=prof_det.codigo_principal,
            codigo_auxiliar=prof_det.codigo_auxiliar,
            descripcion=prof_det.descripcion,
            cantidad=prof_det.cantidad,
            unidad_medida=prof_det.unidad_medida,
            precio_unitario=prof_det.precio_unitario,
            descuento=prof_det.descuento,
            precio_total_sin_impuestos=prof_det.precio_total_sin_impuestos,
            iva_codigo=prof_det.iva_codigo,
            iva_porcentaje=prof_det.iva_porcentaje,
            iva_valor=prof_det.iva_valor,
            ice_codigo=prof_det.ice_codigo,
            ice_porcentaje=prof_det.ice_porcentaje,
            ice_valor=prof_det.ice_valor,
        )
        db.add(comp_det)

    # Update proforma
    proforma.estado = ProformaEstado.CONVERTIDA
    proforma.comprobante_convertido_id = comprobante.id

    await db.flush()

    logger.info(
        f"Proforma {proforma.secuencial} convertida a Factura {secuencial}"
    )

    return {
        "message": "Proforma convertida a Factura exitosamente.",
        "comprobante_id": str(comprobante.id),
        "secuencial": secuencial,
        "clave_acceso": clave_acceso,
    }

"""
ContaEC - Endpoints de Proformas
CRUD de proformas, envío, conversión a factura
"""
import io
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import effective_owner_id
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


def _calcular_totales_proforma(detalles: list, propina: Decimal | None = None) -> dict:
    """Calcula los totales de la proforma a partir de los detalles.

    La propina (monto fijo en dólares) se suma al total final.
    """
    propina = (propina or Decimal("0")).quantize(Decimal("0.01"))
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

    total_con_impuestos = (subtotal_sin_impuestos + total_iva + total_ice + propina).quantize(Decimal("0.01"))

    return {
        "subtotal_sin_impuestos": subtotal_sin_impuestos.quantize(Decimal("0.01")),
        "total_iva": total_iva.quantize(Decimal("0.01")),
        "total_ice": total_ice.quantize(Decimal("0.01")),
        "total_descuento": total_descuento.quantize(Decimal("0.01")),
        "propina": propina,
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
        company = await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

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

        # Calculate totals (la propina se suma al total)
        totales = _calcular_totales_proforma(data.detalles, propina=data.propina)

        # Guardar la propina en info_adicional para referencia (no hay columna propia)
        info_adicional = dict(data.info_adicional) if data.info_adicional else {}
        if data.propina is not None:
            info_adicional["propina"] = str(data.propina)

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
            # Una proforma creada desde el wizard es una proforma REALIZADA/CERRADA (no un borrador)
            estado=ProformaEstado.CERRADA,
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
            info_adicional=json.dumps(info_adicional) if info_adicional else None,
        )
        db.add(proforma)
        await db.flush()

        for i, det_data in enumerate(data.detalles):
            det_result = totales["detalle_resultados"][i]

            # Los items ingresados manualmente (sin product_id) se registran también
            # como producto del catálogo (menú de Productos).
            product_id = det_data.product_id
            if not product_id and det_data.codigo_principal:
                from app.models.product import Product

                existing = await db.execute(
                    select(Product).where(
                        Product.company_id == data.company_id,
                        Product.codigo_principal == det_data.codigo_principal,
                        Product.is_active == True,
                    )
                )
                existing_product = existing.scalars().first()
                if existing_product:
                    product_id = existing_product.id
                else:
                    new_product = Product(
                        company_id=data.company_id,
                        codigo_principal=det_data.codigo_principal,
                        codigo_auxiliar=det_data.codigo_auxiliar,
                        descripcion=det_data.descripcion,
                        tipo="B",
                        precio_unitario=det_data.precio_unitario,
                        iva_codigo=det_data.iva_codigo,
                        iva_porcentaje=det_data.iva_porcentaje,
                        ice_codigo=det_data.ice_codigo,
                        ice_porcentaje=det_data.ice_porcentaje,
                        unidad_medida=det_data.unidad_medida or "Unidad",
                    )
                    db.add(new_product)
                    await db.flush()
                    product_id = new_product.id

            detalle = ProformaDetalle(
                proforma_id=proforma.id,
                product_id=product_id,
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
        .where(Company.user_id == effective_owner_id(current_user))
        .where(Proforma.is_active == True)
        .order_by(Proforma.fecha_emision.desc())
    )

    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
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
        .where(Company.user_id == effective_owner_id(current_user))
        .where(Proforma.is_active == True)
    )

    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        base_query = base_query.where(Proforma.company_id == company_id)

    result = await db.execute(base_query)
    proformas = result.scalars().all()

    stats = {
        "total": len(proformas),
        "borrador": 0,
        "cerrada": 0,
        "enviada": 0,
        "aceptada": 0,
        "rechazada": 0,
        "convertida": 0,
    }

    for p in proformas:
        estado = p.estado
        if estado == ProformaEstado.BORRADOR:
            stats["borrador"] += 1
        elif estado == ProformaEstado.CERRADA:
            stats["cerrada"] += 1
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

    await _get_company_for_user(db, proforma.company_id, effective_owner_id(current_user))

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

    await _get_company_for_user(db, proforma.company_id, effective_owner_id(current_user))

    if proforma.estado not in (ProformaEstado.BORRADOR, ProformaEstado.CERRADA):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden editar proformas en estado BORRADOR o CERRADA.",
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

        totales = _calcular_totales_proforma(data.detalles, propina=data.propina)

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

    # Propina: si se proporciona sin detalles, recalcular el total con la propina actual
    if data.propina is not None and data.detalles is None:
        propina = data.propina
        totales = _calcular_totales_proforma(proforma.detalles, propina=propina)
        proforma.total_con_impuestos = totales["total_con_impuestos"]
    elif data.propina is not None and data.detalles is not None:
        propina = data.propina
    else:
        propina = None

    if propina is not None:
        info_adicional = {}
        if proforma.info_adicional:
            try:
                info_adicional = json.loads(proforma.info_adicional)
            except Exception:
                info_adicional = {}
        if propina:
            info_adicional["propina"] = str(propina)
        else:
            info_adicional.pop("propina", None)
        proforma.info_adicional = json.dumps(info_adicional) if info_adicional else None

    if data.info_adicional is not None:
        merged = dict(data.info_adicional)
        if proforma.info_adicional:
            try:
                merged = {**json.loads(proforma.info_adicional), **merged}
            except Exception:
                pass
        if propina is not None:
            merged["propina"] = str(propina) if propina else "0"
        proforma.info_adicional = json.dumps(merged) if merged else None

    await db.flush()

    return ProformaResponse.model_validate(proforma)


@router.delete("/{proforma_id}")
async def delete_proforma(
    proforma_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar lógicamente una proforma (solo BORRADOR/CERRADA)"""
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

    await _get_company_for_user(db, proforma.company_id, effective_owner_id(current_user))

    if proforma.estado not in (ProformaEstado.BORRADOR, ProformaEstado.CERRADA):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar proformas en estado BORRADOR o CERRADA.",
        )

    proforma.is_active = False
    await db.flush()

    return {"message": "Proforma eliminada exitosamente."}


def _generar_pdf_proforma(proforma: Proforma, company: Company) -> bytes:
    """Genera el PDF de una proforma (documento sin valor fiscal) usando reportlab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ProformaTitle", parent=styles["Title"], fontSize=18, spaceAfter=4
    )
    sub_style = ParagraphStyle(
        "ProformaSub", parent=styles["Normal"], fontSize=9, textColor=colors.grey
    )
    label_style = ParagraphStyle(
        "ProformaLbl", parent=styles["Normal"], fontSize=8, textColor=colors.grey
    )
    value_style = ParagraphStyle(
        "ProformaVal", parent=styles["Normal"], fontSize=9
    )
    bold_style = ParagraphStyle(
        "ProformaBold", parent=styles["Normal"], fontSize=9, fontName="Helvetica-Bold"
    )

    elements = []

    # Encabezado
    elements.append(Paragraph("PROFORMA", title_style))
    elements.append(Paragraph(
        f"<b>{company.razon_social}</b><br/>RUC: {company.ruc} &nbsp;|&nbsp; {company.dir_matriz or ''}",
        sub_style,
    ))
    elements.append(Spacer(1, 10))

    # Datos del documento
    header_data = [
        [
            Paragraph(f"<b>Proforma N°</b><br/>{proforma.secuencial}", value_style),
            Paragraph(f"<b>Fecha Emisión</b><br/>{proforma.fecha_emision.strftime('%d/%m/%Y')}", value_style),
            Paragraph(
                f"<b>Cliente</b><br/>{proforma.cliente_razon_social}<br/>{proforma.cliente_identificacion}",
                value_style,
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[2.2 * inch, 2.0 * inch, 3.0 * inch])
    header_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F5F5")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 14))

    # Detalles
    det_rows = [[
        Paragraph("<b>Código</b>", label_style),
        Paragraph("<b>Descripción</b>", label_style),
        Paragraph("<b>Cant.</b>", label_style),
        Paragraph("<b>P. Unit.</b>", label_style),
        Paragraph("<b>IVA %</b>", label_style),
        Paragraph("<b>Subtotal</b>", label_style),
    ]]
    for det in proforma.detalles:
        det_rows.append([
            Paragraph(det.codigo_principal or "", label_style),
            Paragraph(det.descripcion or "", label_style),
            Paragraph(str(det.cantidad), label_style),
            Paragraph(f"${float(det.precio_unitario):,.2f}", label_style),
            Paragraph(str(det.iva_porcentaje), label_style),
            Paragraph(f"${float(det.precio_total_sin_impuestos):,.2f}", label_style),
        ])

    det_table = Table(det_rows, colWidths=[1.0 * inch, 3.2 * inch, 0.6 * inch, 1.0 * inch, 0.7 * inch, 1.2 * inch])
    det_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (2, 1), (5, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0F0F0")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(det_table)
    elements.append(Spacer(1, 14))

    # Totales
    propina = Decimal("0")
    if proforma.info_adicional:
        try:
            info = json.loads(proforma.info_adicional)
            propina = Decimal(str(info.get("propina", "0")))
        except Exception:
            propina = Decimal("0")

    total_rows = [
        ["Subtotal sin impuestos", f"${float(proforma.subtotal_sin_impuestos):,.2f}"],
        ["IVA", f"${float(proforma.total_iva):,.2f}"],
        ["ICE", f"${float(proforma.total_ice):,.2f}"],
        ["Propina", f"${float(propina):,.2f}"],
        ["TOTAL", f"${float(proforma.total_con_impuestos):,.2f}"],
    ]
    total_table = Table(total_rows, colWidths=[3.0 * inch, 1.6 * inch])
    total_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 4), (-1, 4), colors.HexColor("#1B5E20")),
        ("TEXTCOLOR", (0, 4), (-1, 4), colors.white),
        ("FONTNAME", (0, 4), (-1, 4), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(total_table)

    if proforma.observaciones:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<b>Observaciones:</b> {proforma.observaciones}", value_style))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        "Este documento es una cotización/proforma y NO tiene validez fiscal ante el SRI.",
        sub_style,
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


@router.get("/{proforma_id}/pdf")
async def download_proforma_pdf(
    proforma_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Descargar la proforma en PDF (documento sin valor fiscal)."""
    from fastapi.responses import Response
    from sqlalchemy.orm import selectinload

    proforma_id = validate_uuid(proforma_id, "proforma_id")
    result = await db.execute(
        select(Proforma)
        .options(selectinload(Proforma.detalles))
        .where(Proforma.id == proforma_id, Proforma.is_active == True)
    )
    proforma = result.scalars().first()
    if not proforma:
        raise HTTPException(status_code=404, detail="Proforma no encontrada.")

    company = await _get_company_for_user(db, proforma.company_id, effective_owner_id(current_user))
    pdf_bytes = _generar_pdf_proforma(proforma, company)

    filename = f"Proforma_{proforma.secuencial}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{proforma_id}/enviar")
async def enviar_proforma(
    proforma_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enviar la proforma al cliente.

    Las proformas NO se envían al SRI: se envía un correo con el PDF al correo
    del cliente registrado (o consumidor final). Si el cliente no tiene correo,
    se marca como enviada y el frontend ofrece descargar el PDF.
    """
    from sqlalchemy.orm import selectinload

    proforma_id = validate_uuid(proforma_id, "proforma_id")
    result = await db.execute(
        select(Proforma)
        .options(selectinload(Proforma.detalles))
        .where(Proforma.id == proforma_id, Proforma.is_active == True)
    )
    proforma = result.scalars().first()

    if not proforma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proforma no encontrada.",
        )

    company = await _get_company_for_user(db, proforma.company_id, effective_owner_id(current_user))

    if proforma.estado not in (ProformaEstado.BORRADOR, ProformaEstado.CERRADA):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La proforma debe estar en estado BORRADOR o CERRADA para enviarla. Estado actual: {proforma.estado}",
        )

    # Generar el PDF y enviarlo por correo al cliente (si tiene correo registrado)
    email_result = None
    pdf_bytes = _generar_pdf_proforma(proforma, company)

    if proforma.cliente_email:
        from app.core.email_service import send_proforma_email

        email_result = await send_proforma_email(
            to_email=proforma.cliente_email,
            cliente_razon_social=proforma.cliente_razon_social or "Cliente",
            empresa_razon_social=company.razon_social,
            secuencial=proforma.secuencial,
            total=f"{float(proforma.total_con_impuestos):,.2f}",
            pdf_content=pdf_bytes,
        )

    proforma.estado = ProformaEstado.ENVIADA
    await db.flush()

    message = "Proforma marcada como enviada."
    if email_result and email_result.get("success"):
        message = f"Proforma enviada por correo a {proforma.cliente_email}."
    elif proforma.cliente_email:
        message = (
            "Proforma marcada como enviada, pero NO se pudo enviar el correo: "
            f"{email_result.get('message') if email_result else 'error desconocido'}"
        )
    else:
        message = "Proforma marcada como enviada. El cliente no tiene correo registrado; puede descargar el PDF."

    return {
        "message": message,
        "estado": proforma.estado,
        "email_sent": bool(email_result and email_result.get("success")),
        "download_available": True,
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

    company = await _get_company_for_user(db, proforma.company_id, effective_owner_id(current_user))

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

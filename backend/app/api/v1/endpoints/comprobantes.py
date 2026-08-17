"""
ContaEC - Endpoints de Comprobantes Electrónicos
CRUD de comprobantes, firma digital, envío al SRI, consulta de autorización
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.permissions import effective_owner_id
from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.encryption import decrypt_field
from app.core.ride_generator import generate_ride_pdf
from app.core.security import get_current_user
from app.core.xml_generator import generate_clave_acceso
from app.core.xml_signer import XMLSignerError, sign_xml
from app.models.client import Client
from app.models.company import Company
from app.models.comprobante import Comprobante, ComprobanteDetalle, ComprobanteEstado
from app.models.product import Product
from app.models.user import User, UserConfig
from app.schemas.comprobante import (
    CorreccionRequest,
    ComprobanteCreate,
    ComprobanteListResponse,
    ComprobanteResponse,
    ComprobanteStatsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/comprobantes", tags=["Comprobantes"])
settings = get_settings()


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


async def _get_client_for_company(
    db: AsyncSession,
    client_id: str,
    company_id: str,
) -> Client:
    """
    Obtiene un cliente verificando que pertenezca a la empresa.
    
    Raises:
        HTTPException: Si el cliente no existe o no pertenece a la empresa
    """
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.company_id == company_id,
            Client.is_active == True,
        )
    )
    client = result.scalars().first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado o no pertenece a la empresa.",
        )
    return client


def _calcular_totales(detalles: list) -> dict:
    """
    Calcula los totales del comprobante a partir de los detalles.
    
    Para cada detalle:
    - precio_total_sin_impuestos = cantidad * precio_unitario - descuento
    - iva_valor = precio_total_sin_impuestos * (iva_porcentaje / 100)
    - ice_valor = precio_total_sin_impuestos * (ice_porcentaje / 100) si aplica
    
    Luego agrega:
    - subtotal_sin_impuestos = suma de precio_total_sin_impuestos
    - total_iva = suma de iva_valor
    - total_ice = suma de ice_valor
    - total_descuento = suma de descuento
    - total_con_impuestos = subtotal_sin_impuestos + total_iva + total_ice
    - Subtotales agrupados por porcentaje de IVA
    
    Returns:
        Diccionario con todos los totales calculados
    """
    subtotal_sin_impuestos = Decimal("0")
    total_iva = Decimal("0")
    total_ice = Decimal("0")
    total_descuento = Decimal("0")
    
    # Subtotales agrupados por porcentaje de IVA
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
        # Calcular el descuento efectivo según su tipo:
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

        # Calcular precio total sin impuestos
        precio_total = det.cantidad * det.precio_unitario - descuento_monto
        precio_total = precio_total.quantize(Decimal("0.01"))
        
        # Calcular IVA
        iva_valor = (precio_total * (det.iva_porcentaje / 100)).quantize(Decimal("0.01"))
        
        # Calcular ICE (si aplica)
        ice_valor = Decimal("0")
        if det.ice_porcentaje:
            ice_valor = (precio_total * (det.ice_porcentaje / 100)).quantize(Decimal("0.01"))
        
        # Acumular totales
        subtotal_sin_impuestos += precio_total
        total_iva += iva_valor
        total_ice += ice_valor
        total_descuento += descuento_monto
        
        # Agrupar por porcentaje de IVA
        porc = det.iva_porcentaje
        if porc == Decimal("0"):
            # Distinguir entre 0%, no objeto y exento según el código IVA
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
            # Porcentaje no estándar, agregar a IVA 0
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
# Endpoints CRUD
# ==========================================

@router.post("", response_model=ComprobanteResponse, status_code=status.HTTP_201_CREATED)
async def create_comprobante(
    data: ComprobanteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crear un nuevo comprobante electrónico.
    
    Proceso:
    1. Validar que la empresa pertenece al usuario
    2. Validar que el cliente pertenece a la empresa
    3. Calcular totales a partir de los detalles (subtotal, IVA, ICE, descuentos)
    4. Obtener el siguiente secuencial de la empresa
    5. Generar la clave de acceso del SRI
    6. Crear los registros Comprobante + ComprobanteDetalle
    7. Establecer estado = BORRADOR
    8. Retornar el comprobante creado
    """
    data.client_id = clean_uuid_param(data.client_id, "client_id")
    data.comprobante_modificado_id = clean_uuid_param(data.comprobante_modificado_id, "comprobante_modificado_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    # 1. Validar empresa
    company = await _get_company_for_user(db, data.company_id, effective_owner_id(current_user))

    # 1b. Validar límite de comprobantes mensuales
    from app.core.utils import get_license_limits

    limits = get_license_limits(current_user)
    max_comprobantes = limits['max_comprobantes_month']

    # Contar comprobantes emitidos este mes por la empresa
    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await db.execute(
        select(func.count(Comprobante.id)).where(
            Comprobante.company_id == data.company_id,
            Comprobante.created_at >= first_of_month,
        )
    )
    current_count = result.scalar() or 0

    if current_count >= max_comprobantes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Límite de comprobantes mensuales alcanzado. Tu plan actual permite {max_comprobantes} comprobantes este mes. "
                   f"Contacta a soporte para actualizar tu licencia."
        )

    # 1c. Obtener configuración del usuario para determinar ambiente
    result_config = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    user_config = result_config.scalars().first()
    
    # Determinar ambiente del comprobante según la configuración del usuario
    # Cada usuario puede cambiar entre sandbox y producción independientemente de la empresa
    if user_config and user_config.environment_mode == "production":
        ambiente = "2"  # Producción
    else:
        ambiente = "1"  # Pruebas (sandbox)
    
    # 2. Validar cliente
    client = await _get_client_for_company(db, data.client_id, data.company_id)
    
    # 3. Calcular totales
    totales = _calcular_totales(data.detalles)
    
    # 4. Obtener siguiente secuencial
    secuencial = company.get_next_secuencial(data.tipo_comprobante)
    
    # 5. Generar clave de acceso (usar el ambiente determinado por el usuario, no el de la empresa)
    fecha_emision = datetime.now(timezone.utc)
    try:
        clave_acceso = generate_clave_acceso(
            fecha_emision=fecha_emision.date(),
            tipo_comprobante=data.tipo_comprobante,
            ruc=company.ruc,
            ambiente=ambiente,
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
    
    # 6. Crear Comprobante
    comprobante = Comprobante(
        company_id=data.company_id,
        client_id=data.client_id,
        user_id=current_user.id,
        tipo_comprobante=data.tipo_comprobante,
        secuencial=secuencial,
        fecha_emision=fecha_emision,
        clave_acceso=clave_acceso,
        estado=ComprobanteEstado.BORRADOR,
        ambiente=ambiente,
        tipo_emision=company.tipo_emision,
        # Información del cliente (desnormalizada para XML del SRI)
        cliente_tipo_identificacion=client.tipo_identificacion,
        cliente_identificacion=client.identificacion,
        cliente_razon_social=client.razon_social,
        cliente_direccion=client.direccion,
        cliente_email=client.email,
        cliente_telefono=client.telefono,
        # Totales
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
        # Forma de pago
        forma_pago=data.forma_pago,
        # Retenciones (si aplica)
        retencion_iva_codigo=data.retencion_iva_codigo,
        retencion_iva_porcentaje=data.retencion_iva_porcentaje,
        retencion_renta_codigo=data.retencion_renta_codigo,
        retencion_renta_porcentaje=data.retencion_renta_porcentaje,
        # Notas de crédito/débito
        comprobante_modificado_id=data.comprobante_modificado_id,
        motivo_modificacion=data.motivo_modificacion,
        # Info adicional
        info_adicional=json.dumps(data.info_adicional) if data.info_adicional else None,
    )
    db.add(comprobante)
    await db.flush()
    
    # 6b. Crear ComprobanteDetalle para cada línea
    for i, det_data in enumerate(data.detalles):
        det_result = totales["detalle_resultados"][i]

        # Los items ingresados manualmente (sin product_id) se registran también
        # como producto del catálogo, para que aparezcan en el menú de Productos.
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

        detalle = ComprobanteDetalle(
            comprobante_id=comprobante.id,
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
    
    # Calcular retenciones si se proporcionaron
    if data.retencion_iva_codigo and data.retencion_iva_porcentaje:
        comprobante.retencion_iva_valor = (
            totales["total_iva"] * (data.retencion_iva_porcentaje / 100)
        ).quantize(Decimal("0.01"))
    
    if data.retencion_renta_codigo and data.retencion_renta_porcentaje:
        comprobante.retencion_renta_valor = (
            totales["subtotal_sin_impuestos"] * (data.retencion_renta_porcentaje / 100)
        ).quantize(Decimal("0.01"))
    
    await db.flush()
    
    logger.info(
        f"Comprobante creado: tipo={data.tipo_comprobante}, "
        f"secuencial={secuencial}, empresa={company.ruc}"
    )

    # Recargar con los detalles cargados explícitamente (evita lazy-load en async:
    # MissingGreenlet: greenlet_spawn has not been called)
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Comprobante)
        .options(selectinload(Comprobante.detalles))
        .where(Comprobante.id == comprobante.id)
    )
    comprobante = result.scalars().first()
    
    return ComprobanteResponse.model_validate(comprobante)


@router.get("", response_model=list[ComprobanteListResponse])
async def list_comprobantes(
    company_id: str | None = None,
    tipo_comprobante: str | None = None,
    estado: str | None = None,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(50, ge=1, le=200, description="Número máximo de registros"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar comprobantes del usuario, opcionalmente filtrados por empresa, tipo o estado.
    """
    company_id = clean_company_id(company_id)
    # Construir consulta base: solo comprobantes de empresas del usuario
    query = (
        select(Comprobante)
        .join(Company, Comprobante.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
        .where(Comprobante.is_active == True)
        .order_by(Comprobante.fecha_emision.desc())
    )
    
    # Aplicar filtros opcionales
    if company_id:
        # Verificar que la empresa pertenezca al usuario
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        query = query.where(Comprobante.company_id == company_id)
    
    if tipo_comprobante:
        query = query.where(Comprobante.tipo_comprobante == tipo_comprobante)
    
    if estado:
        query = query.where(Comprobante.estado == estado)
    
    # Aplicar paginación
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    comprobantes = result.scalars().all()
    
    return [ComprobanteListResponse.model_validate(c) for c in comprobantes]


@router.get("/stats", response_model=ComprobanteStatsResponse)
async def get_comprobante_stats(
    company_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener estadísticas de comprobantes para el dashboard.
    
    Incluye conteo por estado y monto total de comprobantes autorizados.
    """
    company_id = clean_company_id(company_id)
    # Consulta base: comprobantes de empresas del usuario
    base_query = (
        select(Comprobante)
        .join(Company, Comprobante.company_id == Company.id)
        .where(Company.user_id == effective_owner_id(current_user))
        .where(Comprobante.is_active == True)
    )
    
    if company_id:
        await _get_company_for_user(db, company_id, effective_owner_id(current_user))
        base_query = base_query.where(Comprobante.company_id == company_id)
    
    # Obtener todos los comprobantes para calcular estadísticas
    result = await db.execute(base_query)
    comprobantes = result.scalars().all()
    
    # Calcular estadísticas
    stats = {
        "total": len(comprobantes),
        "borrador": 0,
        "firmado": 0,
        "enviado": 0,
        "autorizado": 0,
        "rechazado": 0,
        "total_amount": Decimal("0"),
    }
    
    for comp in comprobantes:
        estado = comp.estado
        if estado == ComprobanteEstado.BORRADOR:
            stats["borrador"] += 1
        elif estado == ComprobanteEstado.FIRMADO:
            stats["firmado"] += 1
        elif estado == ComprobanteEstado.ENVIADO:
            stats["enviado"] += 1
        elif estado == ComprobanteEstado.AUTORIZADO:
            stats["autorizado"] += 1
            stats["total_amount"] += comp.total_con_impuestos
        elif estado == ComprobanteEstado.RECHAZADO:
            stats["rechazado"] += 1
    
    stats["total_amount"] = stats["total_amount"].quantize(Decimal("0.01"))
    
    return ComprobanteStatsResponse(**stats)


@router.get("/{comprobante_id}", response_model=ComprobanteResponse)
async def get_comprobante(
    comprobante_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener un comprobante específico con sus detalles.
    
    Verifica que el comprobante pertenezca a una empresa del usuario.
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Comprobante)
        .options(selectinload(Comprobante.detalles))
        .where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()
    
    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )
    
    # Verificar que la empresa pertenezca al usuario
    await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))
    
    return ComprobanteResponse.model_validate(comprobante)


@router.post("/{comprobante_id}/firmar")
async def firmar_comprobante(
    comprobante_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Firmar un comprobante con la firma digital del usuario.
    
    Proceso:
    1. Obtener comprobante (debe estar en estado BORRADOR)
    2. Obtener firma digital del usuario y descifrar contraseña
    3. Generar el XML del comprobante
    4. Firmar el XML con XAdES-BES
    5. Almacenar XML firmado
    6. Actualizar estado a FIRMADO
    7. Retornar vista previa del XML firmado
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    # 1. Obtener comprobante
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()
    
    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )
    
    # Verificar empresa del usuario
    await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))
    
    # Validar estado
    if comprobante.estado != ComprobanteEstado.BORRADOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El comprobante debe estar en estado BORRADOR para firmarlo. Estado actual: {comprobante.estado}",
        )
    
    # 2. Obtener firma digital del usuario
    result_config = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    user_config = result_config.scalars().first()
    
    if not user_config or not user_config.digital_signature_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se ha configurado la firma electrónica. Cargue su firma .p12 en Configuración.",
        )
    
    # Descifrar ruta y contraseña de la firma
    try:
        signature_path = decrypt_field(
            user_config.digital_signature_path, settings.ENCRYPTION_KEY
        )
        signature_password = decrypt_field(
            user_config.digital_signature_password, settings.ENCRYPTION_KEY
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al descifrar la firma electrónica: {str(e)}",
        )
    
    # 3. Generar XML del comprobante
    company = comprobante.company
    client_data = {
        "tipo_identificacion": comprobante.cliente_tipo_identificacion or "07",
        "razon_social": comprobante.cliente_razon_social or "CONSUMIDOR FINAL",
        "identificacion": comprobante.cliente_identificacion or "9999999999999",
    }
    
    comprobante_data = {
        "ambiente": comprobante.ambiente,
        "tipo_emision": comprobante.tipo_emision,
        "razon_social": company.razon_social,
        "nombre_comercial": company.nombre_comercial or company.razon_social,
        "ruc": company.ruc,
        "cod_doc": comprobante.tipo_comprobante,
        "estab": company.cod_establecimiento,
        "pto_emi": company.cod_punto_emision,
        "secuencial": comprobante.secuencial,
        "dir_matriz": company.dir_matriz,
        "dir_establecimiento": company.dir_establecimiento,
        "obligado_contabilidad": company.obligado_contabilidad,
        "contribuyente_especial": company.contribuyente_especial,
        "agente_retencion": company.agente_retencion,
        "regimen_rimpe": company.contribuyente_rimpe if company.contribuyente_rimpe else None,
        "fecha_emision": comprobante.fecha_emision.date(),
        "total_sin_impuestos": comprobante.subtotal_sin_impuestos,
        "total_descuento": comprobante.total_descuento,
        "importe_total": comprobante.total_con_impuestos,
        "propina": Decimal("0"),
        "pagos": [
            {
                "forma_pago": comprobante.forma_pago,
                "total": comprobante.total_con_impuestos,
                "plazo": 0,
                "unidad_tiempo": "DIAS",
            }
        ],
        "info_adicional": json.loads(comprobante.info_adicional) if comprobante.info_adicional else None,
    }
    
    # Agregar totales de impuestos agrupados para el XML (incluye tarifa, según formato SRI)
    totales_impuestos = []
    # IVA
    if comprobante.subtotal_iva_0 > 0:
        totales_impuestos.append({
            "codigo": "2",
            "codigo_porcentaje": "0",
            "base_imponible": comprobante.subtotal_iva_0,
            "tarifa": Decimal("0"),
            "valor": Decimal("0"),
        })
    if comprobante.subtotal_iva_5 > 0:
        totales_impuestos.append({
            "codigo": "2",
            "codigo_porcentaje": "5",
            "base_imponible": comprobante.subtotal_iva_5,
            "tarifa": Decimal("5"),
            "valor": (comprobante.subtotal_iva_5 * Decimal("0.05")).quantize(Decimal("0.01")),
        })
    if comprobante.subtotal_iva_8 > 0:
        totales_impuestos.append({
            "codigo": "2",
            "codigo_porcentaje": "8",
            "base_imponible": comprobante.subtotal_iva_8,
            "tarifa": Decimal("8"),
            "valor": (comprobante.subtotal_iva_8 * Decimal("0.08")).quantize(Decimal("0.01")),
        })
    if comprobante.subtotal_iva_12 > 0:
        totales_impuestos.append({
            "codigo": "2",
            "codigo_porcentaje": "2",
            "base_imponible": comprobante.subtotal_iva_12,
            "tarifa": Decimal("12"),
            "valor": (comprobante.subtotal_iva_12 * Decimal("0.12")).quantize(Decimal("0.01")),
        })
    if comprobante.subtotal_iva_13 > 0:
        totales_impuestos.append({
            "codigo": "2",
            "codigo_porcentaje": "10",
            "base_imponible": comprobante.subtotal_iva_13,
            "tarifa": Decimal("13"),
            "valor": (comprobante.subtotal_iva_13 * Decimal("0.13")).quantize(Decimal("0.01")),
        })
    if comprobante.subtotal_iva_14 > 0:
        totales_impuestos.append({
            "codigo": "2",
            "codigo_porcentaje": "3",
            "base_imponible": comprobante.subtotal_iva_14,
            "tarifa": Decimal("14"),
            "valor": (comprobante.subtotal_iva_14 * Decimal("0.14")).quantize(Decimal("0.01")),
        })
    if comprobante.subtotal_iva_15 > 0:
        totales_impuestos.append({
            "codigo": "2",
            "codigo_porcentaje": "4",
            "base_imponible": comprobante.subtotal_iva_15,
            "tarifa": Decimal("15"),
            "valor": (comprobante.subtotal_iva_15 * Decimal("0.15")).quantize(Decimal("0.01")),
        })
    if comprobante.subtotal_no_objeto_iva > 0:
        totales_impuestos.append({
            "codigo": "2",
            "codigo_porcentaje": "6",
            "base_imponible": comprobante.subtotal_no_objeto_iva,
            "tarifa": Decimal("0"),
            "valor": Decimal("0"),
        })
    if comprobante.subtotal_exento_iva > 0:
        totales_impuestos.append({
            "codigo": "2",
            "codigo_porcentaje": "7",
            "base_imponible": comprobante.subtotal_exento_iva,
            "tarifa": Decimal("0"),
            "valor": Decimal("0"),
        })
    
    comprobante_data["totales_impuestos"] = totales_impuestos
    
    # Detalles para el XML
    detalles_data = []
    for det in comprobante.detalles:
        impuestos_det = [
            {
                "codigo": "2",
                "codigo_porcentaje": det.iva_codigo,
                "tarifa": det.iva_porcentaje,
                "base_imponible": det.precio_total_sin_impuestos,
                "valor": det.iva_valor,
            }
        ]
        if det.ice_codigo and det.ice_porcentaje:
            impuestos_det.append({
                "codigo": "3",
                "codigo_porcentaje": det.ice_codigo,
                "tarifa": det.ice_porcentaje,
                "base_imponible": det.precio_total_sin_impuestos,
                "valor": det.ice_valor or Decimal("0"),
            })
        
        detalles_data.append({
            "codigo_principal": det.codigo_principal,
            "codigo_auxiliar": det.codigo_auxiliar,
            "descripcion": det.descripcion,
            "cantidad": det.cantidad,
            "precio_unitario": det.precio_unitario,
            "descuento": det.descuento,
            "precio_total_sin_impuesto": det.precio_total_sin_impuestos,
            "impuestos": impuestos_det,
        })
    
    # Generar XML según tipo de comprobante
    from app.core.xml_generator import (
        generate_comprobante_retencion_xml,
        generate_factura_xml,
        generate_guia_remision_xml,
        generate_liquidacion_compra_xml,
        generate_nota_credito_xml,
        generate_nota_debito_xml,
    )
    
    company_data = {}  # Los datos de empresa ya están en comprobante_data
    
    # Pasar la clave de acceso ya generada y almacenada en el comprobante
    # para que el XML use la misma clave (consistencia DB ↔ XML)
    existing_clave = comprobante.clave_acceso
    
    tipo = comprobante.tipo_comprobante
    try:
        if tipo == "01":
            xml_content = generate_factura_xml(
                comprobante_data, company_data, client_data, detalles_data,
                clave_acceso=existing_clave,
            )
        elif tipo == "03":
            xml_content = generate_liquidacion_compra_xml(
                comprobante_data, company_data, client_data, detalles_data,
                clave_acceso=existing_clave,
            )
        elif tipo == "04":
            xml_content = generate_nota_credito_xml(
                comprobante_data, company_data, client_data, detalles_data,
                clave_acceso=existing_clave,
            )
        elif tipo == "05":
            xml_content = generate_nota_debito_xml(
                comprobante_data, company_data, client_data, detalles_data,
                clave_acceso=existing_clave,
            )
        elif tipo == "06":
            xml_content = generate_guia_remision_xml(
                comprobante_data, company_data, client_data,
                clave_acceso=existing_clave,
            )
        elif tipo == "07":
            xml_content = generate_comprobante_retencion_xml(
                comprobante_data, company_data, client_data,
                clave_acceso=existing_clave,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de comprobante no soportado para XML: {tipo}",
            )
    except Exception as e:
        logger.error(f"Error generando XML para comprobante {comprobante_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el XML del comprobante: {str(e)}",
        )

    # 3b. Validate XML against SRI XSD schema
    from app.core.xml_generator import validate_xml_against_xsd
    xsd_errors = validate_xml_against_xsd(xml_content, tipo)
    if xsd_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"XML no valida contra el esquema SRI: {'; '.join(xsd_errors)}",
        )

    # 4. Firmar el XML
    try:
        signed_xml = await sign_xml(
            xml_content=xml_content,
            signature_path=signature_path,
            signature_password=signature_password,
        )
    except XMLSignerError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al firmar el comprobante: {str(e)}",
        )
    
    # 5. Almacenar XML firmado
    comprobante.xml_content = signed_xml
    comprobante.estado = ComprobanteEstado.FIRMADO
    
    await db.flush()
    
    logger.info(
        f"Comprobante firmado: tipo={tipo}, secuencial={comprobante.secuencial}"
    )
    
    return {
        "message": "Comprobante firmado exitosamente.",
        "comprobante_id": str(comprobante.id),
        "estado": comprobante.estado,
        "secuencial": comprobante.secuencial,
        "clave_acceso": comprobante.clave_acceso,
        "xml_preview": signed_xml[:500] + "..." if len(signed_xml) > 500 else signed_xml,
    }


@router.post("/{comprobante_id}/enviar")
async def enviar_comprobante_sri(
    comprobante_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enviar un comprobante firmado al SRI para recepción.
    
    Proceso:
    1. Obtener comprobante (debe estar en estado FIRMADO)
    2. Enviar al SRI usando el servicio web de Recepción
    3. Si RECIBIDA: actualizar estado a ENVIADO (luego consultar autorización)
    4. Si DEVUELTA: actualizar estado a RECHAZADO con mensajes de error
    5. Retornar estado actualizado del comprobante
    
    Nota: La autorización es un paso separado (consultar endpoint).
    El servicio de Recepción solo devuelve RECIBIDA o DEVUELTA.
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    # Obtener comprobante
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()
    
    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )
    
    # Verificar empresa del usuario
    await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))
    
    # Validar estado
    if comprobante.estado != ComprobanteEstado.FIRMADO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El comprobante debe estar en estado FIRMADO para enviarlo al SRI. Estado actual: {comprobante.estado}",
        )
    
    # Verificar que existe el XML firmado
    if not comprobante.xml_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El comprobante no tiene XML firmado. Fírmelo primero.",
        )
    
    # Enviar al SRI usando el servicio SOAP
    try:
        from app.core.sri_service import (
            SRIServiceError,
            enviar_comprobante as sri_enviar,
        )
        
        resultado = await sri_enviar(
            xml_firmado=comprobante.xml_content,
            ambiente=comprobante.ambiente,
        )
        
        # resultado es SRIRecepcionResponse (objeto, no dict)
        # Recepción solo devuelve RECIBIDA o DEVUELTA
        if resultado.is_recibida:
            # El SRI recibió el comprobante, se actualizará al consultar
            comprobante.estado = ComprobanteEstado.ENVIADO
            comprobante.sri_mensaje = "Comprobante recibido por el SRI"
        elif resultado.is_devuelta:
            # El SRI rechazó el comprobante en recepción
            comprobante.estado = ComprobanteEstado.RECHAZADO
            mensajes = [m.mensaje for m in resultado.mensajes]
            comprobante.sri_mensaje = "Comprobante devuelto por el SRI"
            comprobante.sri_mensaje_detallado = json.dumps(
                mensajes, ensure_ascii=False
            )
        else:
            # Respuesta inesperada
            comprobante.estado = ComprobanteEstado.ENVIADO
            comprobante.sri_mensaje = f"Respuesta inesperada del SRI: {resultado.estado}"
        
    except SRIServiceError as e:
        logger.error(f"Error de servicio SRI enviando comprobante: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al comunicarse con el SRI: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error enviando comprobante al SRI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al enviar el comprobante al SRI: {str(e)}",
        )
    
    await db.flush()
    
    logger.info(
        f"Comprobante enviado al SRI: tipo={comprobante.tipo_comprobante}, "
        f"secuencial={comprobante.secuencial}, estado={comprobante.estado}"
    )
    
    return {
        "message": "Comprobante enviado al SRI.",
        "comprobante_id": str(comprobante.id),
        "estado": comprobante.estado,
        "secuencial": comprobante.secuencial,
        "clave_acceso": comprobante.clave_acceso,
        "sri_mensaje": comprobante.sri_mensaje,
        "numero_autorizacion": comprobante.numero_autorizacion,
        "fecha_autorizacion": comprobante.fecha_autorizacion.isoformat() if comprobante.fecha_autorizacion else None,
    }


@router.post("/{comprobante_id}/consultar")
async def consultar_comprobante_sri(
    comprobante_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Consultar el estado de autorización de un comprobante en el SRI.
    
    Para comprobantes en estado ENVIADO que aún no han sido resueltos.
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    # Obtener comprobante
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()
    
    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )
    
    # Verificar empresa del usuario
    await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))
    
    # Validar estado (se puede consultar si está ENVIADO o FIRMADO)
    if comprobante.estado not in (ComprobanteEstado.ENVIADO, ComprobanteEstado.FIRMADO):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden consultar comprobantes en estado ENVIADO o FIRMADO. Estado actual: {comprobante.estado}",
        )
    
    # Consultar al SRI usando el servicio de autorización
    try:
        from app.core.sri_service import (
            SRIServiceError,
            autorizar_comprobante as sri_autorizar,
        )
        
        resultado = await sri_autorizar(
            clave_acceso=comprobante.clave_acceso,
            ambiente=comprobante.ambiente,
        )
        
        # resultado es SRIAutorizacionResponse (objeto tipado)
        if resultado.is_autorizado:
            comprobante.estado = ComprobanteEstado.AUTORIZADO
            comprobante.numero_autorizacion = resultado.numero_autorizacion or comprobante.clave_acceso
            comprobante.fecha_autorizacion = resultado.fecha_autorizacion or datetime.now(timezone.utc)
            comprobante.sri_mensaje = "Comprobante autorizado por el SRI"
        elif resultado.is_no_autorizado:
            comprobante.estado = ComprobanteEstado.RECHAZADO
            mensajes = [m.mensaje for m in resultado.mensajes]
            comprobante.sri_mensaje = "Comprobante no autorizado por el SRI"
            comprobante.sri_mensaje_detallado = json.dumps(
                mensajes, ensure_ascii=False
            )
        elif resultado.is_en_proceso:
            comprobante.sri_mensaje = "Comprobante aún en procesamiento en el SRI"
        else:
            comprobante.sri_mensaje = f"Respuesta inesperada del SRI: {resultado.estado}"
        
    except SRIServiceError as e:
        logger.error(f"Error de servicio SRI consultando comprobante: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al consultar el SRI: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error consultando comprobante en SRI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al consultar el SRI: {str(e)}",
        )
    
    await db.flush()
    
    return {
        "message": "Consulta al SRI realizada.",
        "comprobante_id": str(comprobante.id),
        "estado": comprobante.estado,
        "secuencial": comprobante.secuencial,
        "clave_acceso": comprobante.clave_acceso,
        "sri_mensaje": comprobante.sri_mensaje,
        "numero_autorizacion": comprobante.numero_autorizacion,
        "fecha_autorizacion": comprobante.fecha_autorizacion.isoformat() if comprobante.fecha_autorizacion else None,
    }


@router.post("/{comprobante_id}/recuperar")
async def recuperar_comprobante_sri(
    comprobante_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Recuperar un comprobante enviado al SRI dentro de las 72 horas posteriores a su emisión.
    
    Proceso:
    1. Obtener comprobante (debe estar en estado FIRMADO o ENVIADO)
    2. Validar que no hayan transcurrido más de 72 horas desde fecha_emision
    3. Reenviar el XML firmado al SRI (Recepción) - recuperación de no autorizados
    4. Si RECIBIDA: actualizar a ENVIADO y consultar autorización automáticamente
    5. Si DEVUELTA: actualizar a RECHAZADO con mensajes de error
    6. Retornar estado final del comprobante
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    # Obtener comprobante
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()
    
    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )
    
    # Verificar empresa del usuario
    await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))
    
    # Validar estado (solo FIRMADO o ENVIADO)
    if comprobante.estado not in (ComprobanteEstado.FIRMADO, ComprobanteEstado.ENVIADO):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La recuperación aplica solo a comprobantes en estado FIRMADO o ENVIADO. Estado actual: {comprobante.estado}",
        )
    
    # Verificar que existe el XML firmado
    if not comprobante.xml_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El comprobante no tiene XML firmado. Fírmelo primero.",
        )
    
    # Validar ventana de 72 horas desde la fecha de emisión
    ahora = datetime.now(timezone.utc)
    fecha_emision = comprobante.fecha_emision
    if fecha_emision:
        if fecha_emision.tzinfo is None:
            fecha_emision = fecha_emision.replace(tzinfo=timezone.utc)
        horas_transcurridas = (ahora - fecha_emision).total_seconds() / 3600
        if horas_transcurridas > 72:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "El periodo de recuperación de 72 horas desde la emisión ha vencido. "
                    "Este comprobante ya no puede recuperarse en el SRI."
                ),
            )
    
    # Recuperar: reenviar XML firmado al SRI (operación idempotente)
    try:
        from app.core.sri_service import (
            SRIServiceError,
            recuperar_comprobante as sri_recuperar,
        )
        
        resultado = await sri_recuperar(
            xml_firmado=comprobante.xml_content,
            ambiente=comprobante.ambiente,
        )
        
        if resultado.is_recibida:
            # El SRI confirmó que tiene el comprobante (recuperado)
            comprobante.estado = ComprobanteEstado.ENVIADO
            comprobante.sri_mensaje = "Comprobante recuperado: recibido por el SRI"
        elif resultado.is_devuelta:
            # El SRI devolvió el comprobante (no estaba registrado o tiene errores)
            comprobante.estado = ComprobanteEstado.RECHAZADO
            mensajes = [m.mensaje for m in resultado.mensajes]
            comprobante.sri_mensaje = "Comprobante devuelto por el SRI durante la recuperación"
            comprobante.sri_mensaje_detallado = json.dumps(
                mensajes, ensure_ascii=False
            )
        else:
            comprobante.estado = ComprobanteEstado.ENVIADO
            comprobante.sri_mensaje = f"Respuesta inesperada del SRI: {resultado.estado}"
        
    except SRIServiceError as e:
        logger.error(f"Error de servicio SRI recuperando comprobante: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al comunicarse con el SRI: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error recuperando comprobante en SRI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al recuperar el comprobante del SRI: {str(e)}",
        )
    
    await db.flush()
    
    # Si el SRI confirmó recepción, consultar autorización automáticamente
    if resultado.is_recibida:
        await asyncio.sleep(2)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                from app.core.sri_service import autorizar_comprobante as sri_autorizar
                resultado_auth = await sri_autorizar(
                    clave_acceso=comprobante.clave_acceso,
                    ambiente=comprobante.ambiente,
                )
                
                if resultado_auth.is_autorizado:
                    comprobante.estado = ComprobanteEstado.AUTORIZADO
                    comprobante.numero_autorizacion = resultado_auth.numero_autorizacion or comprobante.clave_acceso
                    comprobante.fecha_autorizacion = resultado_auth.fecha_autorizacion or datetime.now(timezone.utc)
                    comprobante.sri_mensaje = "Comprobante autorizado por el SRI"
                    await db.flush()
                    break
                elif resultado_auth.is_no_autorizado:
                    comprobante.estado = ComprobanteEstado.RECHAZADO
                    mensajes = [m.mensaje for m in resultado_auth.mensajes]
                    comprobante.sri_mensaje = "Comprobante no autorizado por el SRI"
                    comprobante.sri_mensaje_detallado = json.dumps(
                        mensajes, ensure_ascii=False
                    )
                    await db.flush()
                    break
                elif resultado_auth.is_en_proceso:
                    if attempt < max_retries - 1:
                        comprobante.sri_mensaje = f"Comprobante en procesamiento, reintento {attempt + 1}/{max_retries}..."
                        await db.flush()
                        await asyncio.sleep(3)
                    else:
                        comprobante.sri_mensaje = "Comprobante aún en procesamiento en el SRI."
                        await db.flush()
                else:
                    comprobante.sri_mensaje = f"Respuesta inesperada del SRI: {resultado_auth.estado}"
                    await db.flush()
                    break
            except SRIServiceError as e:
                logger.error(f"Error consultando autorización (intento {attempt + 1}): {e}")
                if attempt >= max_retries - 1:
                    comprobante.sri_mensaje = "Comprobante recuperado, pero no se pudo consultar la autorización. Use 'Consultar SRI'."
                    await db.flush()
                    break
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Error consultando autorización: {e}")
                break
    
    logger.info(
        f"Comprobante recuperado: tipo={comprobante.tipo_comprobante}, "
        f"secuencial={comprobante.secuencial}, estado={comprobante.estado}"
    )
    
    return {
        "message": f"Recuperación completada. Estado: {comprobante.estado}",
        "comprobante_id": str(comprobante.id),
        "estado": comprobante.estado,
        "secuencial": comprobante.secuencial,
        "clave_acceso": comprobante.clave_acceso,
        "sri_mensaje": comprobante.sri_mensaje,
        "numero_autorizacion": comprobante.numero_autorizacion,
        "fecha_autorizacion": comprobante.fecha_autorizacion.isoformat() if comprobante.fecha_autorizacion else None,
    }


@router.get("/{comprobante_id}/xml")
async def get_comprobante_xml(
    comprobante_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener el contenido XML de un comprobante (firmado o sin firmar).
    
    Si el comprobante está firmado, retorna el XML firmado.
    Si está en borrador, genera el XML sin firma para vista previa.
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()
    
    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )
    
    # Verificar empresa del usuario
    await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))
    
    # Si tiene XML firmado, retornarlo
    if comprobante.xml_content:
        return {
            "comprobante_id": str(comprobante.id),
            "tipo_comprobante": comprobante.tipo_comprobante,
            "secuencial": comprobante.secuencial,
            "clave_acceso": comprobante.clave_acceso,
            "estado": comprobante.estado,
            "xml_content": comprobante.xml_content,
            "is_signed": comprobante.estado in (
                ComprobanteEstado.FIRMADO,
                ComprobanteEstado.ENVIADO,
                ComprobanteEstado.AUTORIZADO,
            ),
        }
    
    # Si está en borrador, generar XML sin firma para vista previa
    return {
        "comprobante_id": str(comprobante.id),
        "tipo_comprobante": comprobante.tipo_comprobante,
        "secuencial": comprobante.secuencial,
        "clave_acceso": comprobante.clave_acceso,
        "estado": comprobante.estado,
        "xml_content": None,
        "message": "El comprobante aún no ha sido firmado. Genere el XML firmándolo primero.",
        "is_signed": False,
    }


@router.delete("/{comprobante_id}")
async def delete_comprobante(
    comprobante_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Eliminar lógicamente un comprobante (solo si está en estado BORRADOR).
    
    Los comprobantes firmados o enviados no pueden eliminarse
    ya que ya tienen existencia legal o en el SRI.
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()
    
    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )
    
    # Verificar empresa del usuario
    await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))
    
    # Solo se pueden eliminar comprobantes en borrador
    if comprobante.estado != ComprobanteEstado.BORRADOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden eliminar comprobantes en estado BORRADOR. "
                   f"Estado actual: {comprobante.estado}",
        )
    
    # Eliminación lógica
    comprobante.is_active = False
    await db.flush()
    
    logger.info(
        f"Comprobante eliminado (borrador): tipo={comprobante.tipo_comprobante}, "
        f"secuencial={comprobante.secuencial}"
    )
    
    return {"message": "Comprobante eliminado exitosamente."}


@router.post("/{comprobante_id}/enviar-email")
async def enviar_comprobante_email(
    comprobante_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enviar un comprobante AUTORIZADO por correo electrónico al cliente.

    Adjunta el XML firmado y el RIDE en PDF.
    Requiere configuración SMTP en UserConfig.
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    # Obtener comprobante
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()

    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )

    # Verificar empresa del usuario
    company = await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))

    # Solo para comprobantes AUTORIZADOS
    if comprobante.estado != ComprobanteEstado.AUTORIZADO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden enviar por email comprobantes AUTORIZADOS. Estado actual: {comprobante.estado}",
        )

    # Verificar email del cliente
    if not comprobante.cliente_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cliente no tiene correo electrónico configurado.",
        )

    # Obtener configuración SMTP del usuario
    result_config = await db.execute(
        select(UserConfig).where(UserConfig.user_id == current_user.id)
    )
    user_config = result_config.scalars().first()

    if not user_config or not user_config.has_smtp_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se ha configurado el servidor SMTP. Configúrelo en Configuración.",
        )

    if not user_config.smtp_host or not user_config.smtp_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuración SMTP incompleta. Verifique host y usuario.",
        )

    # Obtener contraseña SMTP cifrada
    # The field is smtp_password (encrypted), send_comprobante_email
    # expects smtp_password_encrypted and decrypts it internally
    if not user_config.smtp_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña SMTP no configurada.",
        )
    smtp_password_encrypted_raw = user_config.smtp_password

    # Generar RIDE PDF
    result_det = await db.execute(
        select(ComprobanteDetalle).where(
            ComprobanteDetalle.comprobante_id == comprobante_id
        )
    )
    detalles = result_det.scalars().all()

    comprobante_data = {
        "tipo_comprobante": comprobante.tipo_comprobante,
        "secuencial": comprobante.secuencial,
        "clave_acceso": comprobante.clave_acceso,
        "numero_autorizacion": comprobante.numero_autorizacion,
        "fecha_autorizacion": comprobante.fecha_autorizacion.isoformat() if comprobante.fecha_autorizacion else None,
        "fecha_emision": comprobante.fecha_emision.date() if comprobante.fecha_emision else None,
        "ambiente": comprobante.ambiente,
        "tipo_emision": comprobante.tipo_emision,
        "cliente_tipo_identificacion": comprobante.cliente_tipo_identificacion or "07",
        "cliente_identificacion": comprobante.cliente_identificacion or "9999999999999",
        "cliente_razon_social": comprobante.cliente_razon_social or "CONSUMIDOR FINAL",
        "cliente_direccion": comprobante.cliente_direccion or "",
        "cliente_email": comprobante.cliente_email or "",
        "cliente_telefono": comprobante.cliente_telefono or "",
        "subtotal_sin_impuestos": comprobante.subtotal_sin_impuestos,
        "subtotal_iva_0": comprobante.subtotal_iva_0,
        "subtotal_iva_5": comprobante.subtotal_iva_5,
        "subtotal_iva_8": comprobante.subtotal_iva_8,
        "subtotal_iva_12": comprobante.subtotal_iva_12,
        "subtotal_iva_13": comprobante.subtotal_iva_13,
        "subtotal_iva_14": comprobante.subtotal_iva_14,
        "subtotal_iva_15": comprobante.subtotal_iva_15,
        "subtotal_no_objeto_iva": comprobante.subtotal_no_objeto_iva,
        "subtotal_exento_iva": comprobante.subtotal_exento_iva,
        "total_iva": comprobante.total_iva,
        "total_ice": comprobante.total_ice or Decimal("0"),
        "total_descuento": comprobante.total_descuento,
        "total_con_impuestos": comprobante.total_con_impuestos,
        "retencion_iva_codigo": comprobante.retencion_iva_codigo,
        "retencion_iva_porcentaje": comprobante.retencion_iva_porcentaje,
        "retencion_iva_valor": comprobante.retencion_iva_valor,
        "retencion_renta_codigo": comprobante.retencion_renta_codigo,
        "retencion_renta_porcentaje": comprobante.retencion_renta_porcentaje,
        "retencion_renta_valor": comprobante.retencion_renta_valor,
        "motivo_modificacion": comprobante.motivo_modificacion,
        "fecha_emision_documento_sustento": comprobante.fecha_emision_documento_sustento.isoformat() if comprobante.fecha_emision_documento_sustento else None,
        "info_adicional": json.loads(comprobante.info_adicional) if comprobante.info_adicional else None,
    }

    company_data = {
        "ruc": company.ruc,
        "razon_social": company.razon_social,
        "nombre_comercial": company.nombre_comercial or company.razon_social,
        "dir_matriz": company.dir_matriz or "",
        "dir_establecimiento": company.dir_establecimiento or "",
        "cod_establecimiento": company.cod_establecimiento or "001",
        "cod_punto_emision": company.cod_punto_emision or "001",
        "obligado_contabilidad": company.obligado_contabilidad or "NO",
        "contribuyente_especial": company.contribuyente_especial,
        "contribuyente_rimpe": company.contribuyente_rimpe if hasattr(company, 'contribuyente_rimpe') else None,
        "agente_retencion": company.agente_retencion if hasattr(company, 'agente_retencion') else None,
    }

    detalles_data = [
        {
            "codigo_principal": det.codigo_principal,
            "codigo_auxiliar": det.codigo_auxiliar,
            "descripcion": det.descripcion,
            "cantidad": det.cantidad,
            "unidad_medida": det.unidad_medida or "Unidad",
            "precio_unitario": det.precio_unitario,
            "descuento": det.descuento or Decimal("0"),
            "precio_total_sin_impuestos": det.precio_total_sin_impuestos,
            "iva_codigo": det.iva_codigo,
            "iva_porcentaje": det.iva_porcentaje,
            "iva_valor": det.iva_valor,
            "ice_codigo": det.ice_codigo,
            "ice_porcentaje": det.ice_porcentaje,
            "ice_valor": det.ice_valor,
        }
        for det in detalles
    ]

    # Generar PDF del RIDE
    pdf_bytes = None
    try:
        pdf_bytes = generate_ride_pdf(
            comprobante_data=comprobante_data,
            company_data=company_data,
            detalles_data=detalles_data,
        )
    except Exception as e:
        logger.warning(f"Error generando RIDE PDF para email, se enviará sin PDF: {e}")

    # Enviar correo
    try:
        from app.core.email_service import (
            EmailServiceError,
            send_comprobante_email,
        )

        result = send_comprobante_email(
            to_email=comprobante.cliente_email,
            cliente_razon_social=comprobante.cliente_razon_social or "Cliente",
            tipo_comprobante=comprobante.tipo_comprobante,
            secuencial=comprobante.secuencial,
            clave_acceso=comprobante.clave_acceso or "",
            numero_autorizacion=comprobante.numero_autorizacion or "",
            fecha_autorizacion=comprobante.fecha_autorizacion.isoformat() if comprobante.fecha_autorizacion else "",
            empresa_razon_social=company.razon_social,
            empresa_ruc=company.ruc,
            total_con_impuestos=str(comprobante.total_con_impuestos),
            smtp_host=user_config.smtp_host,
            smtp_port=user_config.smtp_port or 587,
            smtp_user=user_config.smtp_user or "",
            smtp_password_encrypted=smtp_password_encrypted_raw,
            smtp_ssl=user_config.smtp_ssl,
            xml_content=comprobante.xml_content,
            pdf_content=pdf_bytes,
            from_name=company.razon_social,
        )

        if result.get("success"):
            return {"message": result.get("message", "Comprobante enviado exitosamente.")}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Error al enviar el correo."),
            )

    except EmailServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al enviar correo: {str(e)}",
        )


@router.post("/{comprobante_id}/procesar")
async def procesar_comprobante(
    comprobante_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Procesar un comprobante FIRMADO en un solo paso:
    1. Enviar al SRI (Recepción)
    2. Si es RECIBIDA, esperar y consultar autorización
    3. Si sigue EN PROCESO, reintentar hasta 3 veces con delay de 3s
    4. Retornar el estado final del comprobante
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    # Obtener comprobante
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()

    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )

    # Verificar empresa del usuario
    await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))

    # Validar estado: debe ser FIRMADO
    if comprobante.estado != ComprobanteEstado.FIRMADO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El comprobante debe estar en estado FIRMADO para procesarlo. Estado actual: {comprobante.estado}",
        )

    # Verificar que existe el XML firmado
    if not comprobante.xml_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El comprobante no tiene XML firmado. Fírmelo primero.",
        )

    # === PASO 1: Enviar al SRI (Recepción) ===
    try:
        from app.core.sri_service import (
            SRIServiceError,
            enviar_comprobante as sri_enviar,
            autorizar_comprobante as sri_autorizar,
        )

        resultado_envio = await sri_enviar(
            xml_firmado=comprobante.xml_content,
            ambiente=comprobante.ambiente,
        )

        if resultado_envio.is_devuelta:
            # El SRI rechazó en recepción
            comprobante.estado = ComprobanteEstado.RECHAZADO
            mensajes = [m.mensaje for m in resultado_envio.mensajes]
            comprobante.sri_mensaje = "Comprobante devuelto por el SRI"
            comprobante.sri_mensaje_detallado = json.dumps(mensajes, ensure_ascii=False)
            await db.flush()

            return {
                "message": "Comprobante devuelto por el SRI en recepción.",
                "comprobante_id": str(comprobante.id),
                "estado": comprobante.estado,
                "secuencial": comprobante.secuencial,
                "clave_acceso": comprobante.clave_acceso,
                "sri_mensaje": comprobante.sri_mensaje,
                "numero_autorizacion": comprobante.numero_autorizacion,
                "fecha_autorizacion": comprobante.fecha_autorizacion.isoformat() if comprobante.fecha_autorizacion else None,
            }

        # RECIBIDA: Actualizar estado a ENVIADO
        comprobante.estado = ComprobanteEstado.ENVIADO
        comprobante.sri_mensaje = "Comprobante recibido por el SRI"
        await db.flush()

    except SRIServiceError as e:
        logger.error(f"Error de servicio SRI enviando comprobante: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al comunicarse con el SRI: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Error enviando comprobante al SRI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al enviar el comprobante al SRI: {str(e)}",
        )

    # === PASO 2: Esperar y consultar autorización ===
    await asyncio.sleep(2)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resultado_auth = await sri_autorizar(
                clave_acceso=comprobante.clave_acceso,
                ambiente=comprobante.ambiente,
            )

            if resultado_auth.is_autorizado:
                comprobante.estado = ComprobanteEstado.AUTORIZADO
                comprobante.numero_autorizacion = resultado_auth.numero_autorizacion or comprobante.clave_acceso
                comprobante.fecha_autorizacion = resultado_auth.fecha_autorizacion or datetime.now(timezone.utc)
                comprobante.sri_mensaje = "Comprobante autorizado por el SRI"
                await db.flush()
                break

            elif resultado_auth.is_no_autorizado:
                comprobante.estado = ComprobanteEstado.RECHAZADO
                mensajes = [m.mensaje for m in resultado_auth.mensajes]
                comprobante.sri_mensaje = "Comprobante no autorizado por el SRI"
                comprobante.sri_mensaje_detallado = json.dumps(mensajes, ensure_ascii=False)
                await db.flush()
                break

            elif resultado_auth.is_en_proceso:
                if attempt < max_retries - 1:
                    comprobante.sri_mensaje = f"Comprobante en procesamiento, reintento {attempt + 1}/{max_retries}..."
                    await db.flush()
                    await asyncio.sleep(3)
                else:
                    comprobante.sri_mensaje = "Comprobante aún en procesamiento en el SRI después de varios reintentos."
                    await db.flush()
            else:
                comprobante.sri_mensaje = f"Respuesta inesperada del SRI: {resultado_auth.estado}"
                await db.flush()
                break

        except SRIServiceError as e:
            logger.error(f"Error de servicio SRI consultando comprobante (intento {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
            else:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Error al consultar el SRI después de {max_retries} intentos: {str(e)}",
                )
        except Exception as e:
            logger.error(f"Error consultando comprobante en SRI: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al consultar el SRI: {str(e)}",
            )

    logger.info(
        f"Comprobante procesado: tipo={comprobante.tipo_comprobante}, "
        f"secuencial={comprobante.secuencial}, estado={comprobante.estado}"
    )

    return {
        "message": f"Procesamiento completado. Estado: {comprobante.estado}",
        "comprobante_id": str(comprobante.id),
        "estado": comprobante.estado,
        "secuencial": comprobante.secuencial,
        "clave_acceso": comprobante.clave_acceso,
        "sri_mensaje": comprobante.sri_mensaje,
        "numero_autorizacion": comprobante.numero_autorizacion,
        "fecha_autorizacion": comprobante.fecha_autorizacion.isoformat() if comprobante.fecha_autorizacion else None,
    }


@router.get("/{comprobante_id}/ride")
async def download_ride_pdf(
    comprobante_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generar y descargar el RIDE (Representación Impresa de Documento Electrónico)
    en formato PDF para un comprobante electrónico.
    
    Proceso:
    1. Obtener el comprobante con sus detalles, empresa y cliente
    2. Construir los diccionarios de datos necesarios
    3. Generar el PDF usando generate_ride_pdf()
    4. Retornar el PDF como FileResponse
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    # Obtener comprobante con relaciones
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()
    
    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )
    
    # Verificar que la empresa pertenezca al usuario
    company = await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))
    
    # Obtener detalles del comprobante
    result_det = await db.execute(
        select(ComprobanteDetalle).where(
            ComprobanteDetalle.comprobante_id == comprobante_id
        )
    )
    detalles = result_det.scalars().all()
    
    # Obtener cliente (si tiene)
    client_data_dict = {}
    if comprobante.client_id:
        result_client = await db.execute(
            select(Client).where(Client.id == comprobante.client_id)
        )
        client_obj = result_client.scalars().first()
        if client_obj:
            client_data_dict = {
                "tipo_identificacion": client_obj.tipo_identificacion,
                "identificacion": client_obj.identificacion,
                "razon_social": client_obj.razon_social,
                "direccion": client_obj.direccion or "",
                "email": client_obj.email or "",
                "telefono": client_obj.telefono or "",
            }
    
    # Construir comprobante_data
    comprobante_data = {
        "tipo_comprobante": comprobante.tipo_comprobante,
        "secuencial": comprobante.secuencial,
        "clave_acceso": comprobante.clave_acceso,
        "numero_autorizacion": comprobante.numero_autorizacion,
        "fecha_autorizacion": comprobante.fecha_autorizacion.isoformat() if comprobante.fecha_autorizacion else None,
        "fecha_emision": comprobante.fecha_emision.date() if comprobante.fecha_emision else None,
        "ambiente": comprobante.ambiente,
        "tipo_emision": comprobante.tipo_emision,
        # Datos del cliente desnormalizados
        "cliente_tipo_identificacion": comprobante.cliente_tipo_identificacion or "07",
        "cliente_identificacion": comprobante.cliente_identificacion or "9999999999999",
        "cliente_razon_social": comprobante.cliente_razon_social or "CONSUMIDOR FINAL",
        "cliente_direccion": comprobante.cliente_direccion or "",
        "cliente_email": comprobante.cliente_email or "",
        "cliente_telefono": comprobante.cliente_telefono or "",
        # Totales
        "subtotal_sin_impuestos": comprobante.subtotal_sin_impuestos,
        "subtotal_iva_0": comprobante.subtotal_iva_0,
        "subtotal_iva_5": comprobante.subtotal_iva_5,
        "subtotal_iva_8": comprobante.subtotal_iva_8,
        "subtotal_iva_12": comprobante.subtotal_iva_12,
        "subtotal_iva_13": comprobante.subtotal_iva_13,
        "subtotal_iva_14": comprobante.subtotal_iva_14,
        "subtotal_iva_15": comprobante.subtotal_iva_15,
        "subtotal_no_objeto_iva": comprobante.subtotal_no_objeto_iva,
        "subtotal_exento_iva": comprobante.subtotal_exento_iva,
        "total_iva": comprobante.total_iva,
        "total_ice": comprobante.total_ice or Decimal("0"),
        "total_descuento": comprobante.total_descuento,
        "total_con_impuestos": comprobante.total_con_impuestos,
        # Retenciones
        "retencion_iva_codigo": comprobante.retencion_iva_codigo,
        "retencion_iva_porcentaje": comprobante.retencion_iva_porcentaje,
        "retencion_iva_valor": comprobante.retencion_iva_valor,
        "retencion_renta_codigo": comprobante.retencion_renta_codigo,
        "retencion_renta_porcentaje": comprobante.retencion_renta_porcentaje,
        "retencion_renta_valor": comprobante.retencion_renta_valor,
        # Notas de crédito/débito
        "motivo_modificacion": comprobante.motivo_modificacion,
        "fecha_emision_documento_sustento": comprobante.fecha_emision_documento_sustento.isoformat() if comprobante.fecha_emision_documento_sustento else None,
        # Info adicional
        "info_adicional": json.loads(comprobante.info_adicional) if comprobante.info_adicional else None,
    }
    
    # Construir company_data
    company_data = {
        "ruc": company.ruc,
        "razon_social": company.razon_social,
        "nombre_comercial": company.nombre_comercial or company.razon_social,
        "dir_matriz": company.dir_matriz or "",
        "dir_establecimiento": company.dir_establecimiento or "",
        "cod_establecimiento": company.cod_establecimiento or "001",
        "cod_punto_emision": company.cod_punto_emision or "001",
        "obligado_contabilidad": company.obligado_contabilidad or "NO",
        "contribuyente_especial": company.contribuyente_especial,
        "contribuyente_rimpe": company.contribuyente_rimpe if hasattr(company, 'contribuyente_rimpe') else None,
        "agente_retencion": company.agente_retencion if hasattr(company, 'agente_retencion') else None,
    }
    
    # Construir detalles_data
    detalles_data = [
        {
            "codigo_principal": det.codigo_principal,
            "codigo_auxiliar": det.codigo_auxiliar,
            "descripcion": det.descripcion,
            "cantidad": det.cantidad,
            "unidad_medida": det.unidad_medida or "Unidad",
            "precio_unitario": det.precio_unitario,
            "descuento": det.descuento or Decimal("0"),
            "precio_total_sin_impuestos": det.precio_total_sin_impuestos,
            "iva_codigo": det.iva_codigo,
            "iva_porcentaje": det.iva_porcentaje,
            "iva_valor": det.iva_valor,
            "ice_codigo": det.ice_codigo,
            "ice_porcentaje": det.ice_porcentaje,
            "ice_valor": det.ice_valor,
        }
        for det in detalles
    ]
    
    # Generar PDF
    temp_dir = Path(settings.TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(temp_dir / f"ride_{comprobante_id}.pdf")
    
    try:
        pdf_bytes = generate_ride_pdf(
            comprobante_data=comprobante_data,
            company_data=company_data,
            detalles_data=detalles_data,
            output_path=output_path,
        )
    except Exception as e:
        logger.error(f"Error generando RIDE PDF para comprobante {comprobante_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el RIDE PDF: {str(e)}",
        )
    
    logger.info(f"RIDE PDF generado para comprobante {comprobante_id}")
    
    return FileResponse(
        path=output_path,
        filename=f"RIDE_{comprobante.tipo_comprobante}_{comprobante.secuencial}.pdf",
        media_type="application/pdf",
    )


# ==========================================
# SRI Pre-validación
# ==========================================

VALID_IVA_CODES = {"0", "2", "3", "4", "5", "6", "7", "8", "9", "10"}
VALID_FORMAS_PAGO = {"01", "15", "16", "17", "18", "19", "20", "21"}
# tipo_identificacion -> expected length of identificacion
IDENT_LENGTH_MAP = {
    "04": 13,   # RUC
    "05": 10,   # Cédula
    "06": None, # Pasaporte (no fixed length)
    "07": 13,   # Consumidor Final
    "08": None, # Identificación Exterior (no fixed length)
}


@router.post("/{comprobante_id}/validar")
async def validar_comprobante(
    comprobante_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Pre-validar un comprobante antes de firmarlo y enviarlo al SRI.
    
    Verifica que los datos del comprobante cumplan con las reglas del SRI:
    1. RUC de la empresa debe tener 13 dígitos
    2. Identificación del cliente debe coincidir con tipo_identificacion
    3. Totales: suma de detalle precio_total_sin_impuestos = subtotal_sin_impuestos
    4. Códigos IVA válidos (0,2,3,4,5,6,7,8,10)
    5. Secuencial no duplicado para misma empresa+estab+ptoEmi
    6. Forma de pago es un código válido
    7. Para NC/ND (tipo 04/05): comprobante_modificado_id existe y motivo no vacío
    8. Para Retención (tipo 07): período fiscal formato MM/YYYY
    
    Returns:
        { valid: bool, errors: [{field, message}], warnings: [{field, message}] }
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    # Obtener comprobante
    result = await db.execute(
        select(Comprobante).where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()
    
    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )
    
    # Verificar empresa del usuario
    company = await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))
    
    # Validar estado
    if comprobante.estado != ComprobanteEstado.BORRADOR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El comprobante debe estar en estado BORRADOR para validarlo. Estado actual: {comprobante.estado}",
        )
    
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    
    # 1. Validar RUC de la empresa (13 dígitos)
    if not company.ruc or len(company.ruc) != 13 or not company.ruc.isdigit():
        errors.append({
            "field": "company.ruc",
            "message": f"El RUC de la empresa debe tener 13 dígitos. Valor actual: '{company.ruc}'",
        })
    
    # 2. Validar identificación del cliente
    tipo_id = comprobante.cliente_tipo_identificacion
    num_id = comprobante.cliente_identificacion or ""
    
    if tipo_id in IDENT_LENGTH_MAP:
        expected_len = IDENT_LENGTH_MAP[tipo_id]
        if expected_len is not None:
            if len(num_id) != expected_len or not num_id.isdigit():
                tipo_label = {"04": "RUC", "05": "Cédula", "07": "Consumidor Final"}.get(tipo_id, tipo_id)
                errors.append({
                    "field": "cliente_identificacion",
                    "message": f"La identificación del cliente ({tipo_label}) debe tener {expected_len} dígitos. Valor actual: '{num_id}'",
                })
    
    # 3. Validar totales: suma de detalle precio_total_sin_impuestos = subtotal_sin_impuestos
    suma_detalles = sum(
        det.precio_total_sin_impuestos for det in comprobante.detalles
    )
    diff = abs(suma_detalles - comprobante.subtotal_sin_impuestos)
    if diff > Decimal("0.02"):
        errors.append({
            "field": "subtotal_sin_impuestos",
            "message": f"La suma de los detalles ({suma_detalles}) no coincide con el subtotal ({comprobante.subtotal_sin_impuestos}). Diferencia: {diff}",
        })
    
    # 4. Validar códigos IVA
    for i, det in enumerate(comprobante.detalles):
        if det.iva_codigo not in VALID_IVA_CODES:
            errors.append({
                "field": f"detalles[{i}].iva_codigo",
                "message": f"Código IVA inválido: '{det.iva_codigo}'. Códigos válidos: {', '.join(sorted(VALID_IVA_CODES))}",
            })
    
    # 5. Validar secuencial no duplicado para misma empresa+estab+ptoEmi
    duplicate_query = (
        select(Comprobante).where(
            Comprobante.company_id == comprobante.company_id,
            Comprobante.secuencial == comprobante.secuencial,
            Comprobante.id != comprobante.id,
            Comprobante.is_active == True,
        )
    )
    dup_result = await db.execute(duplicate_query)
    duplicate = dup_result.scalars().first()
    if duplicate:
        errors.append({
            "field": "secuencial",
            "message": f"Ya existe un comprobante con el secuencial '{comprobante.secuencial}' para esta empresa/establecimiento/punto de emisión",
        })
    
    # 6. Validar forma de pago
    if comprobante.forma_pago not in VALID_FORMAS_PAGO:
        errors.append({
            "field": "forma_pago",
            "message": f"Código de forma de pago inválido: '{comprobante.forma_pago}'. Códigos válidos: {', '.join(sorted(VALID_FORMAS_PAGO))}",
        })
    
    # 7. Para NC/ND (tipo 04/05): validar comprobante_modificado_id y motivo
    if comprobante.tipo_comprobante in ("04", "05"):
        if not comprobante.comprobante_modificado_id:
            errors.append({
                "field": "comprobante_modificado_id",
                "message": f"Las Notas de {'Crédito' if comprobante.tipo_comprobante == '04' else 'Débito'} deben tener un comprobante modificado",
            })
        else:
            # Verificar que el comprobante modificado existe y está autorizado
            mod_result = await db.execute(
                select(Comprobante).where(
                    Comprobante.id == comprobante.comprobante_modificado_id,
                    Comprobante.is_active == True,
                )
            )
            mod_comp = mod_result.scalars().first()
            if not mod_comp:
                errors.append({
                    "field": "comprobante_modificado_id",
                    "message": "El comprobante modificado no existe",
                })
            elif mod_comp.estado != ComprobanteEstado.AUTORIZADO:
                warnings.append({
                    "field": "comprobante_modificado_id",
                    "message": f"El comprobante modificado no está autorizado (estado: {mod_comp.estado})",
                })
        
        if not comprobante.motivo_modificacion or not comprobante.motivo_modificacion.strip():
            errors.append({
                "field": "motivo_modificacion",
                "message": "Las Notas de Crédito/Débito deben tener un motivo de modificación",
            })
    
    # 8. Para Retención (tipo 07): validar período fiscal formato MM/YYYY
    if comprobante.tipo_comprobante == "07":
        if comprobante.info_adicional:
            try:
                info = json.loads(comprobante.info_adicional) if isinstance(comprobante.info_adicional, str) else comprobante.info_adicional
                periodo = info.get("periodo_fiscal", "")
                if periodo:
                    import re
                    if not re.match(r"^(0[1-9]|1[0-2])/\d{4}$", periodo):
                        errors.append({
                            "field": "periodo_fiscal",
                            "message": f"El período fiscal debe tener formato MM/YYYY. Valor actual: '{periodo}'",
                        })
                else:
                    warnings.append({
                        "field": "periodo_fiscal",
                        "message": "El comprobante de retención no tiene período fiscal definido en info_adicional",
                    })
            except (json.JSONDecodeError, AttributeError):
                warnings.append({
                    "field": "periodo_fiscal",
                    "message": "No se pudo verificar el período fiscal en info_adicional",
                })
        else:
            warnings.append({
                "field": "periodo_fiscal",
                "message": "El comprobante de retención no tiene info_adicional con período fiscal",
            })
    
    is_valid = len(errors) == 0
    
    return {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
    }


# ==========================================
# Corregir comprobante rechazado
# ==========================================

@router.post("/{comprobante_id}/corregir", response_model=ComprobanteResponse)
async def corregir_comprobante(
    comprobante_id: str,
    data: CorreccionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Corregir un comprobante rechazado por el SRI.
    
    Solo funciona para comprobantes en estado RECHAZADO.
    Resetea el comprobante a BORRADOR, limpia xml_content,
    numero_autorizacion, fecha_autorizacion, sri_mensaje.
    Actualiza los campos proporcionados en el body y recalcula totales.
    """
    comprobante_id = validate_uuid(comprobante_id, "comprobante_id")
    # Obtener comprobante
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Comprobante)
        .options(selectinload(Comprobante.detalles))
        .where(
            Comprobante.id == comprobante_id,
            Comprobante.is_active == True,
        )
    )
    comprobante = result.scalars().first()
    
    if not comprobante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comprobante no encontrado.",
        )
    
    # Verificar empresa del usuario
    await _get_company_for_user(db, comprobante.company_id, effective_owner_id(current_user))
    
    # Validar estado: RECHAZADO (corrección SRI) o BORRADOR (edición con errores de validación)
    if comprobante.estado not in (ComprobanteEstado.RECHAZADO, ComprobanteEstado.BORRADOR):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se pueden editar comprobantes en estado RECHAZADO o BORRADOR. Estado actual: {comprobante.estado}",
        )
    
    # Resetear estado y limpiar campos SRI
    comprobante.estado = ComprobanteEstado.BORRADOR
    comprobante.xml_content = None
    comprobante.numero_autorizacion = None
    comprobante.fecha_autorizacion = None
    comprobante.sri_mensaje = None
    comprobante.sri_mensaje_detallado = None
    
    # Actualizar forma_pago si se proporcionó
    if data.forma_pago is not None:
        comprobante.forma_pago = data.forma_pago
    
    # Actualizar motivo_modificacion si se proporcionó
    if data.motivo_modificacion is not None:
        comprobante.motivo_modificacion = data.motivo_modificacion
    
    # Actualizar info_adicional si se proporcionó
    if data.info_adicional is not None:
        comprobante.info_adicional = json.dumps(data.info_adicional) if data.info_adicional else None
    
    # Si se proporcionaron nuevos detalles, reemplazar los existentes y recalcular totales
    if data.detalles:
        # Eliminar detalles existentes
        for det in comprobante.detalles:
            await db.delete(det)
        await db.flush()
        
        # Recalcular totales con nuevos detalles
        totales = _calcular_totales(data.detalles)
        
        # Actualizar totales del comprobante
        comprobante.subtotal_sin_impuestos = totales["subtotal_sin_impuestos"]
        comprobante.subtotal_iva_0 = totales["subtotal_iva_0"]
        comprobante.subtotal_iva_5 = totales["subtotal_iva_5"]
        comprobante.subtotal_iva_8 = totales["subtotal_iva_8"]
        comprobante.subtotal_iva_12 = totales["subtotal_iva_12"]
        comprobante.subtotal_iva_13 = totales["subtotal_iva_13"]
        comprobante.subtotal_iva_14 = totales["subtotal_iva_14"]
        comprobante.subtotal_iva_15 = totales["subtotal_iva_15"]
        comprobante.subtotal_no_objeto_iva = totales["subtotal_no_objeto_iva"]
        comprobante.subtotal_exento_iva = totales["subtotal_exento_iva"]
        comprobante.total_iva = totales["total_iva"]
        comprobante.total_ice = totales["total_ice"]
        comprobante.total_descuento = totales["total_descuento"]
        comprobante.total_con_impuestos = totales["total_con_impuestos"]
        
        # Crear nuevos detalles
        for i, det_data in enumerate(data.detalles):
            det_result = totales["detalle_resultados"][i]
            detalle = ComprobanteDetalle(
                comprobante_id=comprobante.id,
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
        
        # Recalcular retenciones si aplican
        if comprobante.retencion_iva_codigo and comprobante.retencion_iva_porcentaje:
            comprobante.retencion_iva_valor = (
                totales["total_iva"] * (comprobante.retencion_iva_porcentaje / 100)
            ).quantize(Decimal("0.01"))
        
        if comprobante.retencion_renta_codigo and comprobante.retencion_renta_porcentaje:
            comprobante.retencion_renta_valor = (
                totales["subtotal_sin_impuestos"] * (comprobante.retencion_renta_porcentaje / 100)
            ).quantize(Decimal("0.01"))
    
    await db.flush()
    
    logger.info(
        f"Comprobante corregido: tipo={comprobante.tipo_comprobante}, "
        f"secuencial={comprobante.secuencial}, estado={comprobante.estado}"
    )

    return ComprobanteResponse.model_validate(comprobante)


# ==========================================
# Endpoint de Estados
# ==========================================

@router.get("/estados")
async def listar_estados_comprobante():
    """
    Obtener lista de estados posibles del comprobante electrónico.

    Retorna todos los estados con su descripción, siglas SRI equivalentes,
    y si es un estado interno o del SRI.
    """
    from app.schemas.comprobante import (
        ComprobanteEstadoEnum,
        estado_to_sigla,
        sigla_to_estado,
    )

    estados_info = {
        "borrador": {
            "nombre": "Borrador",
            "descripcion": "Comprobante en estado borrador, aún no procesado",
            "tipo": "interno",
            "siglas_sri": None,
            "acciones_permitidas": ["firmar", "validar", "eliminar"],
        },
        "firmado": {
            "nombre": "Firmado",
            "descripcion": "Comprobante firmado digitalmente, pendiente de envío al SRI",
            "tipo": "interno",
            "siglas_sri": None,
            "acciones_permitidas": ["enviar", "procesar"],
        },
        "enviado": {
            "nombre": "Enviado",
            "descripcion": "Comprobante enviado al SRI, pendiente de autorización",
            "tipo": "sri",
            "siglas_sri": "PPR",
            "acciones_permitidas": ["consultar"],
        },
        "autorizado": {
            "nombre": "Autorizado",
            "descripcion": "Comprobante autorizado por el SRI",
            "tipo": "sri",
            "siglas_sri": "AUT",
            "acciones_permitidas": ["anular", "enviar_email", "generar_ride"],
        },
        "rechazado": {
            "nombre": "Rechazado",
            "descripcion": "Comprobante rechazado por el SRI",
            "tipo": "sri",
            "siglas_sri": "NAT",
            "acciones_permitidas": ["corregir"],
        },
        "devuelto": {
            "nombre": "Devuelto",
            "descripcion": "Comprobante devuelto por el SRI para corrección",
            "tipo": "sri",
            "siglas_sri": "DEV",
            "acciones_permitidas": ["corregir"],
        },
        "caducado": {
            "nombre": "Caducado",
            "descripcion": "Comprobante que excedió el tiempo de autorización",
            "tipo": "sri",
            "siglas_sri": "CAD",
            "acciones_permitidas": [],
        },
        "anulado": {
            "nombre": "Anulado",
            "descripcion": "Comprobante anulado por el emisor",
            "tipo": "sri",
            "siglas_sri": "ANU",
            "acciones_permitidas": [],
        },
        "contingencia": {
            "nombre": "Contingencia",
            "descripcion": "Comprobante generado en modo contingencia (offline)",
            "tipo": "sri",
            "siglas_sri": "CON",
            "acciones_permitidas": ["enviar_cuando_online"],
        },
    }

    return {
        "estados": [
            {
                "valor": estado.value,
                "nombre": estados_info.get(estado.value, {}).get("nombre", estado.value),
                "descripcion": estados_info.get(estado.value, {}).get("descripcion", ""),
                "tipo": estados_info.get(estado.value, {}).get("tipo", "desconocido"),
                "siglas_sri": estados_info.get(estado.value, {}).get("siglas_sri"),
                "acciones_permitidas": estados_info.get(estado.value, {}).get("acciones_permitidas", []),
            }
            for estado in ComprobanteEstadoEnum
        ],
        "mapeo_siglas": {
            "PPR": "enviado",
            "AUT": "autorizado",
            "NAT": "rechazado",
            "DEV": "devuelto",
            "CAD": "caducado",
            "ANU": "anulado",
            "CON": "contingencia",
        },
    }

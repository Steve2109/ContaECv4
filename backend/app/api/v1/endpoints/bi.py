"""
ContaEC - Endpoints de Business Intelligence (BI)
Dashboards de KPIs, métricas, alertas inteligentes y exportación Power BI
Fase 11: Business Intelligence & KPI Dashboards
"""
import calendar
import json
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, and_, extract, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.validation import clean_company_id, validate_uuid
from app.core.security import get_current_user
from app.models.user import User, UserConfig
from app.models.company import Company
from app.models.comprobante import Comprobante, ComprobanteDetalle, ComprobanteEstado
from app.models.product import Product
from app.models.client import Client
from app.models.employee import Employee, EstadoEmpleado
from app.models.payroll import RolPago, EstadoRol
from app.models.purchase import CuentaPorPagar
from app.models.kardex import Kardex
from app.models.pos import POSTicket, POSCashSession, CajaEstado
from app.schemas.bi import (
    KPIResponse,
    VentaMensual,
    VentaPorTipo,
    TopProducto,
    TopCliente,
    FlujoEfectivoMensual,
    AlertaBI,
    CuadroMandoResponse,
    KPIsResumen,
    IndicadorCumplimiento,
    TendenciaMensual,
    PowerBIExport,
    FactVentaRow,
    DimProducto,
    DimCliente,
    DimTiempo,
    FactInventarioRow,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/bi", tags=["Business Intelligence"])

# Nombres de meses en español
MESES_ES = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Descripción de tipos de comprobante
TIPOS_COMPROBANTE = {
    "01": "Factura",
    "03": "Liquidación de Compra",
    "04": "Nota de Crédito",
    "05": "Nota de Débito",
    "06": "Guía de Remisión",
    "07": "Comprobante de Retención",
}


def _parse_periodo(periodo: Optional[str]) -> tuple[int, int]:
    """Parse periodo string (MM/YYYY) to (month, year). Defaults to current month."""
    if periodo:
        try:
            parts = periodo.split("/")
            return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            pass
    now = datetime.now(timezone.utc)
    return now.month, now.year


# ==========================================
# 1. GET /bi/kpis - Real-time KPI metrics
# ==========================================

@router.get("/kpis", response_model=KPIResponse)
async def get_kpis(
    company_id: Optional[str] = Query(None, description="ID de la empresa (opcional)"),
    periodo: Optional[str] = Query(None, description="Período MM/YYYY (por defecto mes actual)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene KPIs en tiempo real del negocio"""
    company_id = clean_company_id(company_id)
    mes, anio = _parse_periodo(periodo)

    # Fechas del período actual
    fecha_inicio = datetime(anio, mes, 1, tzinfo=timezone.utc)
    if mes == 12:
        fecha_fin = datetime(anio + 1, 1, 1, tzinfo=timezone.utc)
    else:
        fecha_fin = datetime(anio, mes + 1, 1, tzinfo=timezone.utc)

    # Mes anterior
    if mes == 1:
        mes_ant, anio_ant = 12, anio - 1
    else:
        mes_ant, anio_ant = mes - 1, anio
    fecha_inicio_ant = datetime(anio_ant, mes_ant, 1, tzinfo=timezone.utc)
    fecha_fin_ant = fecha_inicio

    # Base query filter
    def comp_filter(extra_conditions=None):
        conditions = [
            Comprobante.fecha_emision >= text(":fecha_inicio"),
            Comprobante.fecha_emision < text(":fecha_fin"),
            Comprobante.is_active == True,
        ]
        if company_id:
            conditions.append(Comprobante.company_id == company_id)
        if extra_conditions:
            conditions.extend(extra_conditions)
        return and_(*conditions)

    # Ventas totales (AUTORIZADO)
    params = {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin}
    ventas_query = select(func.coalesce(func.sum(Comprobante.total_con_impuestos), 0)).where(
        comp_filter([Comprobante.estado == ComprobanteEstado.AUTORIZADO])
    )
    result = await db.execute(ventas_query, params)
    ventas_totales = result.scalar() or Decimal("0")

    # Ventas mes anterior
    params_ant = {"fecha_inicio": fecha_inicio_ant, "fecha_fin": fecha_fin_ant}
    ventas_ant_query = select(func.coalesce(func.sum(Comprobante.total_con_impuestos), 0)).where(
        and_(
            Comprobante.fecha_emision >= fecha_inicio_ant,
            Comprobante.fecha_emision < fecha_fin_ant,
            Comprobante.estado == ComprobanteEstado.AUTORIZADO,
            Comprobante.is_active == True,
            *(Comprobante.company_id == company_id,) if company_id else (),
        )
    )
    result = await db.execute(ventas_ant_query)
    ventas_mes_anterior = result.scalar() or Decimal("0")

    # Variación ventas
    variacion_ventas = None
    if ventas_mes_anterior and ventas_mes_anterior > 0:
        variacion_ventas = ((ventas_totales - ventas_mes_anterior) / ventas_mes_anterior * 100).quantize(Decimal("0.01"))

    # Comprobantes por estado
    base_conditions = [
        Comprobante.fecha_emision >= fecha_inicio,
        Comprobante.fecha_emision < fecha_fin,
        Comprobante.is_active == True,
    ]
    if company_id:
        base_conditions.append(Comprobante.company_id == company_id)

    emitidos_result = await db.scalar(
        select(func.count(Comprobante.id)).where(and_(*base_conditions))
    )
    comprobantes_emitidos = emitidos_result or 0

    autorizados_conditions = base_conditions + [Comprobante.estado == ComprobanteEstado.AUTORIZADO]
    autorizados_result = await db.scalar(
        select(func.count(Comprobante.id)).where(and_(*autorizados_conditions))
    )
    comprobantes_autorizados = autorizados_result or 0

    rechazados_conditions = base_conditions + [Comprobante.estado == ComprobanteEstado.RECHAZADO]
    rechazados_result = await db.scalar(
        select(func.count(Comprobante.id)).where(and_(*rechazados_conditions))
    )
    comprobantes_rechazados = rechazados_result or 0

    # Tasa de aprobación
    tasa_aprobacion = None
    total_resueltos = comprobantes_autorizados + comprobantes_rechazados
    if total_resueltos > 0:
        tasa_aprobacion = (Decimal(comprobantes_autorizados) / Decimal(total_resueltos) * 100).quantize(Decimal("0.01"))

    # Ticket promedio
    ticket_promedio = Decimal("0")
    if comprobantes_autorizados > 0:
        ticket_promedio = (ventas_totales / Decimal(comprobantes_autorizados)).quantize(Decimal("0.01"))

    # IVA recaudado
    iva_query = select(func.coalesce(func.sum(Comprobante.total_iva), 0)).where(
        and_(*autorizados_conditions)
    )
    result = await db.execute(iva_query)
    iva_recaudado = result.scalar() or Decimal("0")

    # Clientes activos
    client_conditions = [Client.is_active == True]
    if company_id:
        client_conditions.append(Client.company_id == company_id)
    clientes_activos = await db.scalar(
        select(func.count(Client.id)).where(and_(*client_conditions))
    ) or 0

    # Productos vendidos (cantidad total de detalles en comprobantes autorizados)
    productos_vendidos_query = select(func.coalesce(func.sum(ComprobanteDetalle.cantidad), 0)).join(
        Comprobante, ComprobanteDetalle.comprobante_id == Comprobante.id
    ).where(
        and_(
            Comprobante.fecha_emision >= fecha_inicio,
            Comprobante.fecha_emision < fecha_fin,
            Comprobante.estado == ComprobanteEstado.AUTORIZADO,
            Comprobante.is_active == True,
            *(Comprobante.company_id == company_id,) if company_id else (),
        )
    )
    result = await db.execute(productos_vendidos_query)
    productos_vendidos = result.scalar() or Decimal("0")

    # Cuentas por cobrar (we don't have a CxC model, use comprobantes AUTORIZADO without payment tracking)
    # Use accounts payable from purchase model
    cxp_conditions = [
        CuentaPorPagar.estado.in_(["pendiente", "parcial", "vencida"]),
        CuentaPorPagar.is_active == True,
    ]
    if company_id:
        cxp_conditions.append(CuentaPorPagar.company_id == company_id)
    cuentas_por_pagar_result = await db.scalar(
        select(func.coalesce(func.sum(CuentaPorPagar.monto_pendiente), 0)).where(and_(*cxp_conditions))
    )
    cuentas_por_pagar = cuentas_por_pagar_result or Decimal("0")

    # Cuentas por cobrar (from CxC model)
    from app.models.accounting import CuentaPorCobrar, CuentaPorCobrarEstado
    cxc_conditions = [
        CuentaPorCobrar.is_active == True,
        CuentaPorCobrar.estado != CuentaPorCobrarEstado.PAGADA,
    ]
    if company_id:
        cxc_conditions.append(CuentaPorCobrar.company_id == company_id)
    cuentas_por_cobrar_result = await db.scalar(
        select(func.coalesce(func.sum(CuentaPorCobrar.monto_pendiente), 0)).where(and_(*cxc_conditions))
    )
    cuentas_por_cobrar = cuentas_por_cobrar_result or Decimal("0")

    # Inventario valor
    prod_conditions = [Product.is_active == True]
    if company_id:
        prod_conditions.append(Product.company_id == company_id)
    inventario_valor_result = await db.scalar(
        select(func.coalesce(func.sum(Product.stock * Product.precio_unitario), 0)).where(and_(*prod_conditions))
    )
    inventario_valor = inventario_valor_result or Decimal("0")

    # Empleados activos
    emp_conditions = [Employee.estado == EstadoEmpleado.ACTIVO, Employee.is_active == True]
    if company_id:
        emp_conditions.append(Employee.company_id == company_id)
    empleados_activos = await db.scalar(
        select(func.count(Employee.id)).where(and_(*emp_conditions))
    ) or 0

    # Nómina total del período
    nomina_conditions = [
        RolPago.periodo_mes == mes,
        RolPago.periodo_anio == anio,
        RolPago.estado.in_([EstadoRol.APROBADO, EstadoRol.PAGADO]),
        RolPago.is_active == True,
    ]
    if company_id:
        nomina_conditions.append(RolPago.company_id == company_id)
    nomina_total_result = await db.scalar(
        select(func.coalesce(func.sum(RolPago.total_liquido), 0)).where(and_(*nomina_conditions))
    )
    nomina_total = nomina_total_result or Decimal("0")

    # POS ventas y tickets de hoy
    hoy_inicio = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    hoy_fin = hoy_inicio + timedelta(days=1)
    pos_conditions = [
        POSTicket.created_at >= hoy_inicio,
        POSTicket.created_at < hoy_fin,
        POSTicket.estado == "pagado",
    ]
    if company_id:
        pos_conditions.append(POSTicket.company_id == company_id)
    pos_ventas_hoy_result = await db.scalar(
        select(func.coalesce(func.sum(POSTicket.total_con_impuestos), 0)).where(and_(*pos_conditions))
    )
    pos_ventas_hoy = pos_ventas_hoy_result or Decimal("0")
    pos_tickets_hoy = await db.scalar(
        select(func.count(POSTicket.id)).where(and_(*pos_conditions))
    ) or 0

    return KPIResponse(
        ventas_totales=ventas_totales,
        ventas_mes_anterior=ventas_mes_anterior,
        variacion_ventas=variacion_ventas,
        comprobantes_emitidos=comprobantes_emitidos,
        comprobantes_autorizados=comprobantes_autorizados,
        comprobantes_rechazados=comprobantes_rechazados,
        tasa_aprobacion=tasa_aprobacion,
        ticket_promedio=ticket_promedio,
        iva_recaudado=iva_recaudado,
        clientes_activos=clientes_activos,
        productos_vendidos=productos_vendidos,
        cuentas_por_cobrar=cuentas_por_cobrar,
        cuentas_por_pagar=cuentas_por_pagar,
        inventario_valor=inventario_valor,
        empleados_activos=empleados_activos,
        nomina_total=nomina_total,
        pos_ventas_hoy=pos_ventas_hoy,
        pos_tickets_hoy=pos_tickets_hoy,
    )


# ==========================================
# 2. GET /bi/ventas-mensuales - Monthly sales chart data
# ==========================================

@router.get("/ventas-mensuales", response_model=list[VentaMensual])
async def get_ventas_mensuales(
    company_id: Optional[str] = Query(None, description="ID de la empresa"),
    anio: Optional[int] = Query(None, description="Año (por defecto actual)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene datos de ventas mensuales para gráficos"""
    company_id = clean_company_id(company_id)
    if not anio:
        anio = datetime.now(timezone.utc).year

    results = []
    for mes in range(1, 13):
        fecha_inicio = datetime(anio, mes, 1, tzinfo=timezone.utc)
        if mes == 12:
            fecha_fin = datetime(anio + 1, 1, 1, tzinfo=timezone.utc)
        else:
            fecha_fin = datetime(anio, mes + 1, 1, tzinfo=timezone.utc)

        conditions = [
            Comprobante.fecha_emision >= fecha_inicio,
            Comprobante.fecha_emision < fecha_fin,
            Comprobante.estado == ComprobanteEstado.AUTORIZADO,
            Comprobante.is_active == True,
        ]
        if company_id:
            conditions.append(Comprobante.company_id == company_id)

        total_ventas = await db.scalar(
            select(func.coalesce(func.sum(Comprobante.total_con_impuestos), 0)).where(and_(*conditions))
        ) or Decimal("0")

        total_iva = await db.scalar(
            select(func.coalesce(func.sum(Comprobante.total_iva), 0)).where(and_(*conditions))
        ) or Decimal("0")

        cantidad = await db.scalar(
            select(func.count(Comprobante.id)).where(and_(*conditions))
        ) or 0

        results.append(VentaMensual(
            mes=mes,
            nombre_mes=MESES_ES[mes],
            total_ventas=total_ventas,
            total_iva=total_iva,
            cantidad_comprobantes=cantidad,
        ))

    return results


# ==========================================
# 3. GET /bi/ventas-por-tipo - Sales by document type
# ==========================================

@router.get("/ventas-por-tipo", response_model=list[VentaPorTipo])
async def get_ventas_por_tipo(
    company_id: Optional[str] = Query(None, description="ID de la empresa"),
    periodo: Optional[str] = Query(None, description="Período MM/YYYY"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene ventas agrupadas por tipo de comprobante"""
    company_id = clean_company_id(company_id)
    mes, anio = _parse_periodo(periodo)
    fecha_inicio = datetime(anio, mes, 1, tzinfo=timezone.utc)
    if mes == 12:
        fecha_fin = datetime(anio + 1, 1, 1, tzinfo=timezone.utc)
    else:
        fecha_fin = datetime(anio, mes + 1, 1, tzinfo=timezone.utc)

    conditions = [
        Comprobante.fecha_emision >= fecha_inicio,
        Comprobante.fecha_emision < fecha_fin,
        Comprobante.estado == ComprobanteEstado.AUTORIZADO,
        Comprobante.is_active == True,
    ]
    if company_id:
        conditions.append(Comprobante.company_id == company_id)

    query = select(
        Comprobante.tipo_comprobante,
        func.coalesce(func.sum(Comprobante.total_con_impuestos), 0).label("total"),
        func.count(Comprobante.id).label("cantidad"),
    ).where(
        and_(*conditions)
    ).group_by(Comprobante.tipo_comprobante)

    result = await db.execute(query)
    rows = result.all()

    return [
        VentaPorTipo(
            tipo_comprobante=row.tipo_comprobante,
            descripcion=TIPOS_COMPROBANTE.get(row.tipo_comprobante, "Otro"),
            total=row.total,
            cantidad=row.cantidad,
        )
        for row in rows
    ]


# ==========================================
# 4. GET /bi/top-productos - Top selling products
# ==========================================

@router.get("/top-productos", response_model=list[TopProducto])
async def get_top_productos(
    company_id: Optional[str] = Query(None, description="ID de la empresa"),
    limite: int = Query(10, ge=1, le=100, description="Número de productos a retornar"),
    periodo: Optional[str] = Query(None, description="Período MM/YYYY"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene los productos más vendidos"""
    company_id = clean_company_id(company_id)
    mes, anio = _parse_periodo(periodo)
    fecha_inicio = datetime(anio, mes, 1, tzinfo=timezone.utc)
    if mes == 12:
        fecha_fin = datetime(anio + 1, 1, 1, tzinfo=timezone.utc)
    else:
        fecha_fin = datetime(anio, mes + 1, 1, tzinfo=timezone.utc)

    comp_conditions = [
        Comprobante.fecha_emision >= fecha_inicio,
        Comprobante.fecha_emision < fecha_fin,
        Comprobante.estado == ComprobanteEstado.AUTORIZADO,
        Comprobante.is_active == True,
    ]
    if company_id:
        comp_conditions.append(Comprobante.company_id == company_id)

    query = select(
        ComprobanteDetalle.product_id,
        ComprobanteDetalle.codigo_principal,
        ComprobanteDetalle.descripcion,
        func.coalesce(func.sum(ComprobanteDetalle.cantidad), 0).label("cantidad_vendida"),
        func.coalesce(func.sum(ComprobanteDetalle.precio_total_sin_impuestos), 0).label("total_venta"),
    ).join(
        Comprobante, ComprobanteDetalle.comprobante_id == Comprobante.id
    ).where(
        and_(*comp_conditions, ComprobanteDetalle.product_id != None)
    ).group_by(
        ComprobanteDetalle.product_id,
        ComprobanteDetalle.codigo_principal,
        ComprobanteDetalle.descripcion,
    ).order_by(
        text("total_venta DESC")
    ).limit(limite)

    result = await db.execute(query)
    rows = result.all()

    return [
        TopProducto(
            product_id=row.product_id,
            codigo=row.codigo_principal,
            descripcion=row.descripcion,
            cantidad_vendida=row.cantidad_vendida,
            total_venta=row.total_venta,
        )
        for row in rows
    ]


# ==========================================
# 5. GET /bi/top-clientes - Top clients by purchase amount
# ==========================================

@router.get("/top-clientes", response_model=list[TopCliente])
async def get_top_clientes(
    company_id: Optional[str] = Query(None, description="ID de la empresa"),
    limite: int = Query(10, ge=1, le=100, description="Número de clientes a retornar"),
    periodo: Optional[str] = Query(None, description="Período MM/YYYY"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene los clientes con mayor volumen de compras"""
    company_id = clean_company_id(company_id)
    mes, anio = _parse_periodo(periodo)
    fecha_inicio = datetime(anio, mes, 1, tzinfo=timezone.utc)
    if mes == 12:
        fecha_fin = datetime(anio + 1, 1, 1, tzinfo=timezone.utc)
    else:
        fecha_fin = datetime(anio, mes + 1, 1, tzinfo=timezone.utc)

    conditions = [
        Comprobante.fecha_emision >= fecha_inicio,
        Comprobante.fecha_emision < fecha_fin,
        Comprobante.estado == ComprobanteEstado.AUTORIZADO,
        Comprobante.is_active == True,
        Comprobante.client_id != None,
    ]
    if company_id:
        conditions.append(Comprobante.company_id == company_id)

    query = select(
        Comprobante.client_id,
        Comprobante.cliente_identificacion,
        Comprobante.cliente_razon_social,
        func.coalesce(func.sum(Comprobante.total_con_impuestos), 0).label("total_compras"),
        func.count(Comprobante.id).label("cantidad_comprobantes"),
    ).where(
        and_(*conditions)
    ).group_by(
        Comprobante.client_id,
        Comprobante.cliente_identificacion,
        Comprobante.cliente_razon_social,
    ).order_by(
        text("total_compras DESC")
    ).limit(limite)

    result = await db.execute(query)
    rows = result.all()

    return [
        TopCliente(
            client_id=row.client_id,
            identificacion=row.cliente_identificacion or "N/A",
            razon_social=row.cliente_razon_social or "N/A",
            total_compras=row.total_compras,
            cantidad_comprobantes=row.cantidad_comprobantes,
        )
        for row in rows
    ]


# ==========================================
# 6. GET /bi/flujo-efectivo - Cash flow summary
# ==========================================

@router.get("/flujo-efectivo", response_model=list[FlujoEfectivoMensual])
async def get_flujo_efectivo(
    company_id: Optional[str] = Query(None, description="ID de la empresa"),
    anio: Optional[int] = Query(None, description="Año (por defecto actual)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene resumen de flujo de efectivo mensual"""
    company_id = clean_company_id(company_id)
    if not anio:
        anio = datetime.now(timezone.utc).year

    results = []
    for mes in range(1, 13):
        fecha_inicio = datetime(anio, mes, 1, tzinfo=timezone.utc)
        if mes == 12:
            fecha_fin = datetime(anio + 1, 1, 1, tzinfo=timezone.utc)
        else:
            fecha_fin = datetime(anio, mes + 1, 1, tzinfo=timezone.utc)

        # Ingresos = ventas autorizadas
        ing_conditions = [
            Comprobante.fecha_emision >= fecha_inicio,
            Comprobante.fecha_emision < fecha_fin,
            Comprobante.estado == ComprobanteEstado.AUTORIZADO,
            Comprobante.is_active == True,
        ]
        if company_id:
            ing_conditions.append(Comprobante.company_id == company_id)
        ingresos = await db.scalar(
            select(func.coalesce(func.sum(Comprobante.total_con_impuestos), 0)).where(and_(*ing_conditions))
        ) or Decimal("0")

        # Egresos = cuentas por pagar del período + nómina
        cxp_conditions = [
            CuentaPorPagar.fecha_emision >= fecha_inicio,
            CuentaPorPagar.fecha_emision < fecha_fin,
            CuentaPorPagar.is_active == True,
            CuentaPorPagar.estado.in_(["pendiente", "parcial", "pagada", "vencida"]),
        ]
        if company_id:
            cxp_conditions.append(CuentaPorPagar.company_id == company_id)
        egresos_cxp = await db.scalar(
            select(func.coalesce(func.sum(CuentaPorPagar.monto_total), 0)).where(and_(*cxp_conditions))
        ) or Decimal("0")

        # Nómina
        nom_conditions = [
            RolPago.periodo_mes == mes,
            RolPago.periodo_anio == anio,
            RolPago.estado.in_([EstadoRol.APROBADO, EstadoRol.PAGADO]),
            RolPago.is_active == True,
        ]
        if company_id:
            nom_conditions.append(RolPago.company_id == company_id)
        egresos_nomina = await db.scalar(
            select(func.coalesce(func.sum(RolPago.total_liquido), 0)).where(and_(*nom_conditions))
        ) or Decimal("0")

        egresos = egresos_cxp + egresos_nomina
        flujo_neto = ingresos - egresos

        results.append(FlujoEfectivoMensual(
            mes=mes,
            ingresos=ingresos,
            egresos=egresos,
            flujo_neto=flujo_neto,
        ))

    return results


# ==========================================
# 7. GET /bi/alertas - Smart alerts
# ==========================================

@router.get("/alertas", response_model=list[AlertaBI])
async def get_alertas(
    company_id: Optional[str] = Query(None, description="ID de la empresa"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene alertas inteligentes del sistema"""
    company_id = clean_company_id(company_id)
    now = datetime.now(timezone.utc)
    alertas = []
    alert_counter = 0

    def make_alert(tipo: str, titulo: str, mensaje: str, categoria: str) -> AlertaBI:
        nonlocal alert_counter
        alert_counter += 1
        return AlertaBI(
            id=f"alert-{alert_counter}",
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            fecha=now,
            categoria=categoria,
        )

    # 1. Comprobantes rechazados sin corregir
    rech_conditions = [
        Comprobante.estado == ComprobanteEstado.RECHAZADO,
        Comprobante.is_active == True,
    ]
    if company_id:
        rech_conditions.append(Comprobante.company_id == company_id)
    rechazados_count = await db.scalar(
        select(func.count(Comprobante.id)).where(and_(*rech_conditions))
    ) or 0
    if rechazados_count > 0:
        alertas.append(make_alert(
            tipo="danger",
            titulo="Comprobantes rechazados",
            mensaje=f"Hay {rechazados_count} comprobante(s) rechazado(s) por el SRI que requieren corrección.",
            categoria="comprobantes",
        ))

    # 2. Firmas digitales por expirar (< 30 días)
    thirty_days = now + timedelta(days=30)
    firmas_conditions = [
        UserConfig.signature_expiry_date != None,
        UserConfig.signature_expiry_date <= thirty_days,
        UserConfig.signature_expiry_date >= now,
    ]
    firmas_expiring = await db.scalar(
        select(func.count(UserConfig.id)).where(and_(*firmas_conditions))
    ) or 0
    if firmas_expiring > 0:
        alertas.append(make_alert(
            tipo="warning",
            titulo="Firmas digitales por expirar",
            mensaje=f"Hay {firmas_expiring} firma(s) digital(es) que expirarán en los próximos 30 días.",
            categoria="firmas",
        ))

    # 3. Licencia por expirar
    user_license_end = current_user.license_end_date
    if user_license_end and user_license_end <= thirty_days and user_license_end >= now:
        days_left = (user_license_end - now).days
        alertas.append(make_alert(
            tipo="warning",
            titulo="Licencia por expirar",
            mensaje=f"Su licencia expira en {days_left} días. Renueve para evitar interrupciones.",
            categoria="licencia",
        ))
    elif user_license_end and user_license_end < now:
        alertas.append(make_alert(
            tipo="danger",
            titulo="Licencia expirada",
            mensaje="Su licencia ha expirado. Renueve para continuar utilizando el sistema.",
            categoria="licencia",
        ))

    # 4. Productos con stock bajo
    stock_conditions = [
        Product.is_active == True,
        Product.stock_minimo > 0,
        Product.stock <= Product.stock_minimo,
    ]
    if company_id:
        stock_conditions.append(Product.company_id == company_id)
    low_stock_count = await db.scalar(
        select(func.count(Product.id)).where(and_(*stock_conditions))
    ) or 0
    if low_stock_count > 0:
        alertas.append(make_alert(
            tipo="warning",
            titulo="Stock bajo",
            mensaje=f"Hay {low_stock_count} producto(s) con stock igual o menor al mínimo configurado.",
            categoria="inventario",
        ))

    # 5. Cuentas por pagar vencidas
    cxp_venc_conditions = [
        CuentaPorPagar.estado.in_(["pendiente", "vencida"]),
        CuentaPorPagar.fecha_vencimiento != None,
        CuentaPorPagar.fecha_vencimiento < now,
        CuentaPorPagar.is_active == True,
    ]
    if company_id:
        cxp_venc_conditions.append(CuentaPorPagar.company_id == company_id)
    cxp_vencidas_count = await db.scalar(
        select(func.count(CuentaPorPagar.id)).where(and_(*cxp_venc_conditions))
    ) or 0
    if cxp_vencidas_count > 0:
        alertas.append(make_alert(
            tipo="danger",
            titulo="Cuentas por pagar vencidas",
            mensaje=f"Hay {cxp_vencidas_count} cuenta(s) por pagar vencida(s) que requieren atención.",
            categoria="cuentas",
        ))

    # 6. Inventario sin movimiento en 30+ días
    thirty_days_ago = now - timedelta(days=30)
    # Products with no kardex movement in 30 days that have stock > 0
    prod_with_stock_conditions = [
        Product.is_active == True,
        Product.stock > 0,
    ]
    if company_id:
        prod_with_stock_conditions.append(Product.company_id == company_id)

    # Subquery: products with recent movements
    recent_movements = select(Kardex.product_id).where(
        and_(
            Kardex.fecha_movimiento >= thirty_days_ago,
            Kardex.is_active == True,
        )
    )

    stale_inventory_count = await db.scalar(
        select(func.count(Product.id)).where(
            and_(
                *prod_with_stock_conditions,
                Product.id.not_in(recent_movements),
            )
        )
    ) or 0
    if stale_inventory_count > 0:
        alertas.append(make_alert(
            tipo="info",
            titulo="Inventario sin movimiento",
            mensaje=f"Hay {stale_inventory_count} producto(s) con stock pero sin movimiento en los últimos 30 días.",
            categoria="inventario",
        ))

    # 7. IVA pendiente de declaración (simplificado - recordatorio mensual)
    # Check if there are authorized invoices from previous month
    prev_month_date = now.replace(day=1) - timedelta(days=1)
    prev_mes = prev_month_date.month
    prev_anio = prev_month_date.year
    iva_conditions = [
        Comprobante.estado == ComprobanteEstado.AUTORIZADO,
        extract("month", Comprobante.fecha_emision) == prev_mes,
        extract("year", Comprobante.fecha_emision) == prev_anio,
        Comprobante.is_active == True,
        Comprobante.total_iva > 0,
    ]
    if company_id:
        iva_conditions.append(Comprobante.company_id == company_id)
    iva_pendiente = await db.scalar(
        select(func.coalesce(func.sum(Comprobante.total_iva), 0)).where(and_(*iva_conditions))
    ) or Decimal("0")
    if iva_pendiente > 0:
        alertas.append(make_alert(
            tipo="info",
            titulo="IVA pendiente de declaración",
            mensaje=f"Hay ${iva_pendiente:,.2f} de IVA del mes anterior ({MESES_ES[prev_mes]}) pendiente de declaración al SRI.",
            categoria="iva",
        ))

    # 8. Sesiones POS abiertas por mucho tiempo (> 8 horas)
    eight_hours_ago = now - timedelta(hours=8)
    pos_open_conditions = [
        POSCashSession.estado == CajaEstado.ABIERTA,
        POSCashSession.fecha_apertura <= eight_hours_ago,
    ]
    if company_id:
        pos_open_conditions.append(POSCashSession.company_id == company_id)
    open_sessions_count = await db.scalar(
        select(func.count(POSCashSession.id)).where(and_(*pos_open_conditions))
    ) or 0
    if open_sessions_count > 0:
        alertas.append(make_alert(
            tipo="warning",
            titulo="Sesiones POS abiertas",
            mensaje=f"Hay {open_sessions_count} sesión(es) de caja POS abierta(s) por más de 8 horas.",
            categoria="pos",
        ))

    # If no alerts, add a success message
    if not alertas:
        alertas.append(make_alert(
            tipo="success",
            titulo="Todo en orden",
            mensaje="No hay alertas pendientes. El sistema funciona correctamente.",
            categoria="general",
        ))

    return alertas


# ==========================================
# 8. GET /bi/cuadro-mando - Executive dashboard
# ==========================================

@router.get("/cuadro-mando", response_model=CuadroMandoResponse)
async def get_cuadro_mando(
    company_id: Optional[str] = Query(None, description="ID de la empresa"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtiene el Cuadro de Mando ejecutivo con resumen consolidado"""
    company_id = clean_company_id(company_id)
    now = datetime.now(timezone.utc)
    mes_actual = now.month
    anio_actual = now.year

    # KPIs Resumen
    fecha_inicio = datetime(anio_actual, mes_actual, 1, tzinfo=timezone.utc)
    if mes_actual == 12:
        fecha_fin = datetime(anio_actual + 1, 1, 1, tzinfo=timezone.utc)
    else:
        fecha_fin = datetime(anio_actual, mes_actual + 1, 1, tzinfo=timezone.utc)

    # Mes anterior
    if mes_actual == 1:
        mes_ant, anio_ant = 12, anio_actual - 1
    else:
        mes_ant, anio_ant = mes_actual - 1, anio_actual
    fecha_inicio_ant = datetime(anio_ant, mes_ant, 1, tzinfo=timezone.utc)
    fecha_fin_ant = fecha_inicio

    comp_base = [
        Comprobante.fecha_emision >= fecha_inicio,
        Comprobante.fecha_emision < fecha_fin,
        Comprobante.estado == ComprobanteEstado.AUTORIZADO,
        Comprobante.is_active == True,
    ]
    comp_base_ant = [
        Comprobante.fecha_emision >= fecha_inicio_ant,
        Comprobante.fecha_emision < fecha_fin_ant,
        Comprobante.estado == ComprobanteEstado.AUTORIZADO,
        Comprobante.is_active == True,
    ]
    if company_id:
        comp_base.append(Comprobante.company_id == company_id)
        comp_base_ant.append(Comprobante.company_id == company_id)

    ventas_mes = await db.scalar(
        select(func.coalesce(func.sum(Comprobante.total_con_impuestos), 0)).where(and_(*comp_base))
    ) or Decimal("0")

    ventas_ant = await db.scalar(
        select(func.coalesce(func.sum(Comprobante.total_con_impuestos), 0)).where(and_(*comp_base_ant))
    ) or Decimal("0")

    variacion_ventas = None
    if ventas_ant and ventas_ant > 0:
        variacion_ventas = ((ventas_mes - ventas_ant) / ventas_ant * 100).quantize(Decimal("0.01"))

    autorizados_count = await db.scalar(
        select(func.count(Comprobante.id)).where(and_(*comp_base))
    ) or 0

    ticket_promedio = Decimal("0")
    if autorizados_count > 0:
        ticket_promedio = (ventas_mes / Decimal(autorizados_count)).quantize(Decimal("0.01"))

    iva_recaudado = await db.scalar(
        select(func.coalesce(func.sum(Comprobante.total_iva), 0)).where(and_(*comp_base))
    ) or Decimal("0")

    # Cuentas por pagar pendientes
    cxp_conditions = [
        CuentaPorPagar.estado.in_(["pendiente", "parcial", "vencida"]),
        CuentaPorPagar.is_active == True,
    ]
    if company_id:
        cxp_conditions.append(CuentaPorPagar.company_id == company_id)
    cuentas_por_pagar = await db.scalar(
        select(func.coalesce(func.sum(CuentaPorPagar.monto_pendiente), 0)).where(and_(*cxp_conditions))
    ) or Decimal("0")

    # Nómina
    nom_conditions = [
        RolPago.periodo_mes == mes_actual,
        RolPago.periodo_anio == anio_actual,
        RolPago.estado.in_([EstadoRol.APROBADO, EstadoRol.PAGADO]),
        RolPago.is_active == True,
    ]
    if company_id:
        nom_conditions.append(RolPago.company_id == company_id)
    nomina_total = await db.scalar(
        select(func.coalesce(func.sum(RolPago.total_liquido), 0)).where(and_(*nom_conditions))
    ) or Decimal("0")

    # Flujo neto del mes (ingresos - egresos)
    egresos_cxp = await db.scalar(
        select(func.coalesce(func.sum(CuentaPorPagar.monto_total), 0)).where(
            and_(
                CuentaPorPagar.fecha_emision >= fecha_inicio,
                CuentaPorPagar.fecha_emision < fecha_fin,
                CuentaPorPagar.is_active == True,
                CuentaPorPagar.estado.in_(["pendiente", "parcial", "pagada", "vencida"]),
                *(CuentaPorPagar.company_id == company_id,) if company_id else (),
            )
        )
    ) or Decimal("0")
    flujo_neto_mes = ventas_mes - egresos_cxp - nomina_total

    kpis_resumen = KPIsResumen(
        ventas_mes=ventas_mes,
        variacion_ventas=variacion_ventas,
        ticket_promedio=ticket_promedio,
        iva_recaudado=iva_recaudado,
        cuentas_por_cobrar=Decimal("0"),
        cuentas_por_pagar=cuentas_por_pagar,
        flujo_neto_mes=flujo_neto_mes,
        nomina_total=nomina_total,
    )

    # Indicadores de cumplimiento
    indicadores = []

    # Tasa de aprobación SRI
    all_comp_conditions = [
        Comprobante.fecha_emision >= fecha_inicio,
        Comprobante.fecha_emision < fecha_fin,
        Comprobante.is_active == True,
        Comprobante.estado.in_([ComprobanteEstado.AUTORIZADO, ComprobanteEstado.RECHAZADO]),
    ]
    if company_id:
        all_comp_conditions.append(Comprobante.company_id == company_id)
    total_resueltos = await db.scalar(
        select(func.count(Comprobante.id)).where(and_(*all_comp_conditions))
    ) or 0

    aut_conditions = list(all_comp_conditions)
    aut_conditions[-1] = Comprobante.estado == ComprobanteEstado.AUTORIZADO  # Replace the in_ condition
    # Actually re-do properly
    aut_in_conditions = [
        Comprobante.fecha_emision >= fecha_inicio,
        Comprobante.fecha_emision < fecha_fin,
        Comprobante.is_active == True,
        Comprobante.estado == ComprobanteEstado.AUTORIZADO,
    ]
    if company_id:
        aut_in_conditions.append(Comprobante.company_id == company_id)
    aut_count = await db.scalar(
        select(func.count(Comprobante.id)).where(and_(*aut_in_conditions))
    ) or 0

    tasa_aprobacion_sri = Decimal("0")
    if total_resueltos > 0:
        tasa_aprobacion_sri = (Decimal(aut_count) / Decimal(total_resueltos) * 100).quantize(Decimal("0.01"))

    sri_estado = "optimo" if tasa_aprobacion_sri >= 95 else ("aceptable" if tasa_aprobacion_sri >= 80 else "critico")
    indicadores.append(IndicadorCumplimiento(
        nombre="Tasa de aprobación SRI",
        valor=tasa_aprobacion_sri,
        estado=sri_estado,
    ))

    # Comprobantes emitidos vs autorizados (timeliness)
    all_emitidos_conditions = [
        Comprobante.fecha_emision >= fecha_inicio,
        Comprobante.fecha_emision < fecha_fin,
        Comprobante.is_active == True,
    ]
    if company_id:
        all_emitidos_conditions.append(Comprobante.company_id == company_id)
    total_emitidos = await db.scalar(
        select(func.count(Comprobante.id)).where(and_(*all_emitidos_conditions))
    ) or 0

    tasa_emision_aut = Decimal("0")
    if total_emitidos > 0:
        tasa_emision_aut = (Decimal(aut_count) / Decimal(total_emitidos) * 100).quantize(Decimal("0.01"))
    emision_estado = "optimo" if tasa_emision_aut >= 90 else ("aceptable" if tasa_emision_aut >= 70 else "critico")
    indicadores.append(IndicadorCumplimiento(
        nombre="Emisión vs autorización",
        valor=tasa_emision_aut,
        estado=emision_estado,
    ))

    # Completitud de datos (clientes con identificación)
    client_conditions = [Client.is_active == True]
    if company_id:
        client_conditions.append(Client.company_id == company_id)
    total_clients = await db.scalar(
        select(func.count(Client.id)).where(and_(*client_conditions))
    ) or 0
    clients_with_id = await db.scalar(
        select(func.count(Client.id)).where(
            and_(*client_conditions, Client.identificacion != "9999999999999")
        )
    ) or 0
    completitud = Decimal("0")
    if total_clients > 0:
        completitud = (Decimal(clients_with_id) / Decimal(total_clients) * 100).quantize(Decimal("0.01"))
    completitud_estado = "optimo" if completitud >= 80 else ("aceptable" if completitud >= 50 else "critico")
    indicadores.append(IndicadorCumplimiento(
        nombre="Completitud de datos de clientes",
        valor=completitud,
        estado=completitud_estado,
    ))

    # Tendencias (últimos 3 meses)
    tendencias = []
    for i in range(2, -1, -1):
        t_mes = mes_actual - i
        t_anio = anio_actual
        if t_mes <= 0:
            t_mes += 12
            t_anio -= 1

        t_fecha_inicio = datetime(t_anio, t_mes, 1, tzinfo=timezone.utc)
        if t_mes == 12:
            t_fecha_fin = datetime(t_anio + 1, 1, 1, tzinfo=timezone.utc)
        else:
            t_fecha_fin = datetime(t_anio, t_mes + 1, 1, tzinfo=timezone.utc)

        t_conditions = [
            Comprobante.fecha_emision >= t_fecha_inicio,
            Comprobante.fecha_emision < t_fecha_fin,
            Comprobante.estado == ComprobanteEstado.AUTORIZADO,
            Comprobante.is_active == True,
        ]
        if company_id:
            t_conditions.append(Comprobante.company_id == company_id)

        t_ventas = await db.scalar(
            select(func.coalesce(func.sum(Comprobante.total_con_impuestos), 0)).where(and_(*t_conditions))
        ) or Decimal("0")

        t_comprobantes = await db.scalar(
            select(func.count(Comprobante.id)).where(and_(*t_conditions))
        ) or 0

        t_ticket = Decimal("0")
        if t_comprobantes > 0:
            t_ticket = (t_ventas / Decimal(t_comprobantes)).quantize(Decimal("0.01"))

        tendencias.append(TendenciaMensual(
            mes=t_mes,
            nombre_mes=MESES_ES[t_mes],
            ventas=t_ventas,
            comprobantes=t_comprobantes,
            ticket_promedio=t_ticket,
        ))

    # Estado general (0-100) - weighted score
    estado_general = 0
    # Tasa aprobación SRI (weight: 40)
    estado_general += min(40, float(tasa_aprobacion_sri) * 0.4)
    # Emisión vs autorización (weight: 30)
    estado_general += min(30, float(tasa_emision_aut) * 0.3)
    # Completitud datos (weight: 15)
    estado_general += min(15, float(completitud) * 0.15)
    # Variación ventas (weight: 15) - positive variation adds, negative subtracts
    if variacion_ventas is not None:
        var_score = max(-15, min(15, float(variacion_ventas) * 0.15))
        estado_general += var_score + 15  # Normalize to 0-30 range
    else:
        estado_general += 7.5  # Neutral if no data

    estado_general = max(0, min(100, int(estado_general)))

    return CuadroMandoResponse(
        kpis_resumen=kpis_resumen,
        indicadores_cumplimiento=indicadores,
        tendencias=tendencias,
        estado_general=estado_general,
    )


# ==========================================
# 9. GET /bi/export-powerbi - Export data in Power BI format (JSON)
# ==========================================

@router.get("/export-powerbi", response_model=PowerBIExport)
async def export_powerbi(
    company_id: Optional[str] = Query(None, description="ID de la empresa"),
    periodo_desde: Optional[str] = Query(None, description="Período desde MM/YYYY"),
    periodo_hasta: Optional[str] = Query(None, description="Período hasta MM/YYYY"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exporta datos en formato compatible con Power BI (JSON)"""
    company_id = clean_company_id(company_id)

    # Parse date range
    if periodo_desde:
        mes_desde, anio_desde = _parse_periodo(periodo_desde)
    else:
        mes_desde, anio_desde = 1, datetime.now(timezone.utc).year

    if periodo_hasta:
        mes_hasta, anio_hasta = _parse_periodo(periodo_hasta)
    else:
        now = datetime.now(timezone.utc)
        mes_hasta, anio_hasta = now.month, now.year

    fecha_desde = datetime(anio_desde, mes_desde, 1, tzinfo=timezone.utc)

    # Calculate end of periodo_hasta
    if mes_hasta == 12:
        fecha_hasta = datetime(anio_hasta + 1, 1, 1, tzinfo=timezone.utc)
    else:
        fecha_hasta = datetime(anio_hasta, mes_hasta + 1, 1, tzinfo=timezone.utc)

    # === fact_ventas ===
    comp_conditions = [
        Comprobante.fecha_emision >= fecha_desde,
        Comprobante.fecha_emision < fecha_hasta,
        Comprobante.is_active == True,
    ]
    if company_id:
        comp_conditions.append(Comprobante.company_id == company_id)

    comp_query = select(Comprobante).where(and_(*comp_conditions)).order_by(Comprobante.fecha_emision)
    comp_result = await db.execute(comp_query)
    comprobantes = comp_result.scalars().all()

    fact_ventas = []
    for comp in comprobantes:
        # One row per comprobante + detalle combination for granular analysis
        if comp.detalles:
            for det in comp.detalles:
                fact_ventas.append(FactVentaRow(
                    comprobante_id=comp.id,
                    tipo_comprobante=comp.tipo_comprobante,
                    secuencial=comp.secuencial,
                    fecha_emision=comp.fecha_emision.isoformat() if comp.fecha_emision else "",
                    estado=comp.estado,
                    cliente_id=comp.client_id,
                    product_id=det.product_id,
                    cantidad=det.cantidad,
                    precio_unitario=det.precio_unitario,
                    subtotal_sin_impuestos=det.precio_total_sin_impuestos,
                    total_iva=det.iva_valor,
                    total_con_impuestos=comp.total_con_impuestos,
                    iva_porcentaje=det.iva_porcentaje,
                ))
        else:
            fact_ventas.append(FactVentaRow(
                comprobante_id=comp.id,
                tipo_comprobante=comp.tipo_comprobante,
                secuencial=comp.secuencial,
                fecha_emision=comp.fecha_emision.isoformat() if comp.fecha_emision else "",
                estado=comp.estado,
                cliente_id=comp.client_id,
                subtotal_sin_impuestos=comp.subtotal_sin_impuestos,
                total_iva=comp.total_iva,
                total_con_impuestos=comp.total_con_impuestos,
            ))

    # === dim_productos ===
    prod_conditions = [Product.is_active == True]
    if company_id:
        prod_conditions.append(Product.company_id == company_id)
    prod_result = await db.execute(
        select(Product).where(and_(*prod_conditions)).order_by(Product.codigo_principal)
    )
    products = prod_result.scalars().all()

    dim_productos = [
        DimProducto(
            product_id=p.id,
            codigo_principal=p.codigo_principal,
            codigo_auxiliar=p.codigo_auxiliar,
            descripcion=p.descripcion,
            tipo=p.tipo,
            precio_unitario=p.precio_unitario,
            iva_porcentaje=p.iva_porcentaje,
            stock=p.stock,
            is_active=p.is_active,
        )
        for p in products
    ]

    # === dim_clientes ===
    client_conditions = [Client.is_active == True]
    if company_id:
        client_conditions.append(Client.company_id == company_id)
    client_result = await db.execute(
        select(Client).where(and_(*client_conditions)).order_by(Client.razon_social)
    )
    clients = client_result.scalars().all()

    dim_clientes = [
        DimCliente(
            client_id=c.id,
            tipo_identificacion=c.tipo_identificacion,
            identificacion=c.identificacion,
            razon_social=c.razon_social,
            email=c.email,
            is_active=c.is_active,
        )
        for c in clients
    ]

    # === dim_tiempo ===
    dim_tiempo = []
    current = fecha_desde
    while current < fecha_hasta:
        # Generate one entry per day in range
        days_in_month = calendar.monthrange(current.year, current.month)[1]
        for day in range(1, days_in_month + 1):
            try:
                day_date = datetime(current.year, current.month, day, tzinfo=timezone.utc)
                if day_date >= fecha_hasta:
                    break
                weekday = day_date.weekday()  # 0=Monday
                dim_tiempo.append(DimTiempo(
                    fecha=day_date.strftime("%Y-%m-%d"),
                    anio=day_date.year,
                    mes=day_date.month,
                    dia=day_date.day,
                    nombre_mes=MESES_ES[day_date.month],
                    trimestre=(day_date.month - 1) // 3 + 1,
                    semana=day_date.isocalendar()[1],
                    dia_semana=weekday + 1,
                    nombre_dia=DIAS_ES[weekday],
                    es_fin_semana=weekday >= 5,
                ))
            except ValueError:
                continue
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            current = datetime(current.year, current.month + 1, 1, tzinfo=timezone.utc)

    # === fact_inventario ===
    fact_inventario = [
        FactInventarioRow(
            product_id=p.id,
            codigo_principal=p.codigo_principal,
            descripcion=p.descripcion,
            stock=p.stock,
            stock_minimo=p.stock_minimo,
            valor_inventario=(p.stock * p.precio_unitario).quantize(Decimal("0.01")),
            ubicacion=p.ubicacion,
        )
        for p in products
    ]

    return PowerBIExport(
        fact_ventas=fact_ventas,
        dim_productos=dim_productos,
        dim_clientes=dim_clientes,
        dim_tiempo=dim_tiempo,
        fact_inventario=fact_inventario,
    )


# ==========================================
# 10. POST /bi/export-powerbi-file - Download Power BI export as JSON file
# ==========================================

@router.post("/export-powerbi-file")
async def export_powerbi_file(
    company_id: Optional[str] = Query(None, description="ID de la empresa"),
    periodo_desde: Optional[str] = Query(None, description="Período desde MM/YYYY"),
    periodo_hasta: Optional[str] = Query(None, description="Período hasta MM/YYYY"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Descarga la exportación de Power BI como archivo JSON"""
    company_id = clean_company_id(company_id)
    # Reuse the export endpoint logic
    export_data = await export_powerbi(
        company_id=company_id,
        periodo_desde=periodo_desde,
        periodo_hasta=periodo_hasta,
        current_user=current_user,
        db=db,
    )

    # Convert to JSON
    json_content = export_data.model_dump_json(indent=2)

    # Generate filename
    now = datetime.now(timezone.utc)
    filename = f"contaec_powerbi_export_{now.strftime('%Y%m%d_%H%M%S')}.json"

    return JSONResponse(
        content=json.loads(json_content),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )

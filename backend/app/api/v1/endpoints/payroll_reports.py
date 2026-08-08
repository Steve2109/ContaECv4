"""
ContaEC - Endpoints de Reportes SRI Nómina
Reportes: RDEP XML, Anexos IESS, SUT XIII-XIV, Impuesto Renta
"""
import io
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.ir_calculation import (
    calcular_retencion_mensual,
    generar_reporte_ir_empleado,
)
from app.core.security import get_current_user
from app.models.company import Company
from app.models.employee import Employee
from app.models.payroll import RolPago, RolPagoDetalle
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/payroll-reports", tags=["Nómina - Reportes SRI"])


# ==========================================
# RDEP - Reporte de Datos para Impuestos a la Renta
# ==========================================


@router.get("/rdep/xml")
async def generar_rdep_xml(
    company_id: str = Query(..., description="ID de la empresa"),
    anio: int = Query(..., ge=2020, le=2100, description="Año del reporte"),
    employee_id: Optional[str] = Query(None, description="ID del empleado (opcional, todos si no especifica)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generar archivo XML del RDEP (Reporte de Datos para Impuestos a la Renta).

    El RDEP es el reporte anual que las empresas deben presentar al SRI
    con información de ingresos, deducciones y retenciones de empleados.

    Formato según Ficha Técnica SRI paraСОТ 2024.

    **Parámetros:**
    - `company_id`: ID de la empresa
    - `anio`: Año del reporte (ej: 2024)
    - `employee_id`: Empleado específico (opcional, reporta todos si no se indica)

    **Retorna:**
    - Archivo XML descargable con estructura RDEP
    """
    employee_id = clean_uuid_param(employee_id, "employee_id")
    company_id = validate_uuid(company_id, "company_id")
    # Verificar empresa
    company = await _get_company_for_user(db, company_id, current_user.id)
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    # Construir XML RDEP
    xml_content = await _construir_rdep_xml(db, company, anio, employee_id)

    # Retornar como archivo descargable
    return StreamingResponse(
        io.BytesIO(xml_content.encode("utf-8")),
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="RDEP_{company.ruc}_{anio}.xml"'
        },
    )


@router.get("/rdep")
async def obtener_rdep_data(
    company_id: str = Query(..., description="ID de la empresa"),
    anio: int = Query(..., ge=2020, le=2100, description="Año del reporte"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener datos del RDEP en formato JSON.

    **Retorna:**
    - Lista de empleados con ingresos, deducciones y retenciones anuales
    """
    company_id = validate_uuid(company_id, "company_id")
    company = await _get_company_for_user(db, company_id, current_user.id)
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    # Obtener todos los empleados activos
    result = await db.execute(
        select(Employee).where(
            Employee.company_id == company_id,
            Employee.is_active == True,
        )
    )
    empleados = result.scalars().all()

    reporte_empleados = []
    for empleado in empleados:
        # Obtener rol de pago del año
        ingresos_anuales = await _calcular_ingresos_anuales(db, empleado.id, anio)
        retencion_mensual = calcular_retencion_mensual(empleado.sueldo_mensual)

        reporte_empleados.append({
            "empleado_id": empleado.id,
            "nombres": empleado.nombres,
            "apellidos": empleado.apellidos,
            "cedula": empleado.cedula,
            "sueldo_anual": ingresos_anuales,
            "retencion_ir_anual": retencion_mensual * 12,
            "meses_trabajados": 12,  # Simplificado
        })

    return {
        "company_ruc": company.ruc,
        "company_name": company.razon_social,
        "anio": anio,
        "total_empleados": len(reporte_empleados),
        "empleados": reporte_empleados,
    }


# ==========================================
# Anexos IESS
# ==========================================


@router.get("/anexos-iess")
async def generar_anexos_iess(
    company_id: str = Query(..., description="ID de la empresa"),
    periodo_mes: int = Query(..., ge=1, le=12, description="Mes del período"),
    periodo_anio: int = Query(..., ge=2020, le=2100, description="Año del período"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generar Anexo IESS para reporte de aportes patronales y personales.

    El anexo IESS detalla los aportes al Instituto Ecuatoriano de
    Seguridad Social por empleado para un período mensual.

    **Parámetros:**
    - `company_id`: ID de la empresa
    - `periodo_mes`: Mes del período (1-12)
    - `periodo_anio`: Año del período

    **Retorna:**
    - Lista de empleados con aportes personales y patronales
    """
    company_id = validate_uuid(company_id, "company_id")
    company = await _get_company_for_user(db, company_id, current_user.id)
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    # Obtener rol de pago del período
    result = await db.execute(
        select(RolPago).where(
            RolPago.company_id == company_id,
            RolPago.periodo_mes == periodo_mes,
            RolPago.periodo_anio == periodo_anio,
            RolPago.estado == "pagado",
        )
    )
    rol_pago = result.scalars().first()

    if not rol_pago:
        raise HTTPException(404, "No se encontró rol de pago para el período")

    # Generar anexo
    anexo_data = []
    for detalle in rol_pago.detalles:
        anexo_data.append({
            "empleado_id": detalle.employee_id,
            "cedula": detalle.employee.cedula,
            "nombres": detalle.employee.nombre_completo,
            "sueldo_base": str(detalle.sueldo_base),
            "aporte_personal_945": str(detalle.iess_personal_945),
            "aporte_patronal_1115": str(detalle.iess_patronal_1115),
            "apporte_riesgos_0005": str(detalle.iee_0005),
            "secap_002": str(detalle.secap_002),
            "cenaces_001": str(detalle.cenaces_001),
        })

    return {
        "company_ruc": company.ruc,
        "company_name": company.razon_social,
        "periodo": f"{periodo_mes:02d}/{periodo_anio}",
        "total_empleados": len(anexo_data),
        "detalle": anexo_data,
    }


# ==========================================
# SUT XIII-XIV (Síntesis Único de Trabajo)
# ==========================================


@router.get("/sut-xiii-xiv")
async def generar_sut_decimos(
    company_id: str = Query(..., description="ID de la empresa"),
    anio: int = Query(..., ge=2020, le=2100, description="Año del reporte"),
    tipo_decimo: str = Query(..., description="Tipo: 'tercero' o 'cuarto'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generar reporte SUT (Síntesis Único de Trabajo) para Décimo Tercero o Cuarto.

    Reporte consolidado de pagos de décimos realizados en el año.

    **Parámetros:**
    - `company_id`: ID de la empresa
    - `anio`: Año del reporte
    - `tipo_decimo`: 'tercero' (navideño) o 'cuarto' (escolar)

    **Retorna:**
    - Consolidado de pagos de décimos por empleado
    """
    company_id = validate_uuid(company_id, "company_id")
    if tipo_decimo not in ["tercero", "cuarto"]:
        raise HTTPException(400, "tipo_decimo debe ser 'tercero' o 'cuarto'")

    company = await _get_company_for_user(db, company_id, current_user.id)
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    # Obtener empleados con décimos pagados
    from app.models.hr_extended2 import UtilidadesParticipacion
    from app.models.hr_extended import DecimoPago

    result = await db.execute(
        select(DecimoPago).where(
            DecimoPago.company_id == company_id,
            DecimoPago.anio == anio,
            DecimoPago.tipo == tipo_decimo,
            DecimoPago.estado == "pagado",
        )
    )
    decimos = result.scalars().all()

    consolidado = []
    total_pagado = Decimal("0.00")

    for decimo in decimos:
        consolidado.append({
            "empleado_id": decimo.employee_id,
            "cedula": decimo.employee.cedula,
            "nombres": decimo.employee.nombre_completo,
            "tipo": decimo.tipo,
            "anio": decimo.anio,
            "valor_pagado": str(decimo.valor_pagado),
            "fecha_pago": decimo.fecha_pago.isoformat() if decimo.fecha_pago else None,
        })
        total_pagado += decimo.valor_pagado

    return {
        "company_ruc": company.ruc,
        "company_name": company.razon_social,
        "anio": anio,
        "tipo": f"Décimo{' ' if tipo_decimo == 'tercero' else ' '}{tipo_decimo.capitalize()}",
        "total_empleados": len(consolidado),
        "total_pagado": str(total_pagado),
        "detalle": consolidado,
    }


# ==========================================
# Reporte IR Retenciones
# ==========================================


@router.get("/ir-retenciones")
async def reporte_ir_retenciones(
    company_id: str = Query(..., description="ID de la empresa"),
    periodo_mes: int = Query(..., ge=1, le=12, description="Mes del período"),
    periodo_anio: int = Query(..., ge=2020, le=2100, description="Año del período"),
    employee_id: Optional[str] = Query(None, description="ID del empleado (opcional)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reporte de retenciones de Impuesto a la Renta por empleado.

    Muestra el cálculo de retención IR para cada empleado según
    la tabla progresiva vigente.

    **Retorna:**
    - Lista de empleados con base imponible, tasa y retención calculada
    """
    employee_id = clean_uuid_param(employee_id, "employee_id")
    company_id = validate_uuid(company_id, "company_id")
    company = await _get_company_for_user(db, company_id, current_user.id)
    if not company:
        raise HTTPException(404, "Empresa no encontrada")

    # Filtrar por empleado si se indica
    if employee_id:
        result = await db.execute(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.company_id == company_id,
                Employee.is_active == True,
            )
        )
    else:
        result = await db.execute(
            select(Employee).where(
                Employee.company_id == company_id,
                Employee.is_active == True,
            )
        )

    empleados = result.scalars().all()

    reportes = []
    for empleado in empleados:
        # Calcular ingresos anuales proyectados
        ingresos_anuales = await _calcular_ingresos_anuales(db, empleado.id, periodo_anio)

        # Generar reporte IR
        reporte = generar_reporte_ir_empleado(
            empleado_nombre=empleado.nombre_completo,
            sueldo_mensual=empleado.sueldo_mensual,
            ingresos_anuales=ingresos_anuales,
            deducciones=Decimal("0.00"),  # Sin deducciones por defecto
            cargas_familiares=0,  # Sin cargas por defecto
        )
        reportes.append(reporte)

    return {
        "company_ruc": company.ruc,
        "company_name": company.razon_social,
        "periodo": f"{periodo_mes:02d}/{periodo_anio}",
        "total_empleados": len(reportes),
        "reportes": reportes,
    }


# ==========================================
# Funciones auxiliares
# ==========================================


async def _get_company_for_user(
    db: AsyncSession,
    company_id: str,
    user_id: str,
) -> Optional[Company]:
    """Obtiene una empresa verificando que pertenezca al usuario actual"""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == user_id,
            Company.is_active == True,
        )
    )
    return result.scalars().first()


async def _calcular_ingresos_anuales(
    db: AsyncSession,
    employee_id: str,
    anio: int,
) -> Decimal:
    """Calcula ingresos anuales gravados de un empleado"""
    result = await db.execute(
        select(RolPagoDetalle).where(
            RolPagoDetalle.employee_id == employee_id,
        )
    )
    detalles = result.scalars().all()

    total_ingresos = Decimal("0.00")
    for detalle in detalles:
        # Filtrar por año
        rol_result = await db.execute(
            select(RolPago).where(
                RolPago.id == detalle.rol_pago_id,
                RolPago.periodo_anio == anio,
            )
        )
        rol = rol_result.scalars().first()
        if rol:
            total_ingresos += detalle.total_ingresos

    return total_ingresos.quantize(Decimal("0.01"))


async def _construir_rdep_xml(
    db: AsyncSession,
    company: Company,
    anio: int,
    employee_id: Optional[str],
) -> str:
    """Construye el XML del RDEP según formato SRI"""
    # Encabezado XML
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<RDEP xmlns="urn:ec:sgi:rdep">\n'
    xml += f'  <InformacionGeneral>\n'
    xml += f'    <RUC>{company.ruc}</RUC>\n'
    xml += f'    <RazonSocial>{company.razon_social}</RazonSocial>\n'
    xml += f'    <Periodo>{anio}</Periodo>\n'
    xml += f'    <FechaEmision>{datetime.now(timezone.utc).isoformat()}</FechaEmision>\n'
    xml += f'  </InformacionGeneral>\n'
    xml += f'  <Empleados>\n'

    # Obtener empleados
    if employee_id:
        result = await db.execute(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.company_id == company.id,
            )
        )
    else:
        result = await db.execute(
            select(Employee).where(
                Employee.company_id == company.id,
                Employee.is_active == True,
            )
        )

    empleados = result.scalars().all()

    for empleado in empleados:
        ingresos_anuales = await _calcular_ingresos_anuales(db, empleado.id, anio)
        retencion_mensual = calcular_retencion_mensual(empleado.sueldo_mensual)
        retencion_anual = retencion_mensual * 12

        xml += f'    <Empleado>\n'
        xml += f'      <Identificacion>{empleado.cedula}</Identificacion>\n'
        xml += f'      <Apellidos>{empleado.apellidos}</Apellidos>\n'
        xml += f'      <Nombres>{empleado.nombres}</Nombres>\n'
        xml += f'      <IngresosGravados>{ingresos_anuales}</IngresosGravados>\n'
        xml += f'      <RetencionIR>{retencion_anual}</RetencionIR>\n'
        xml += f'    </Empleado>\n'

    xml += f'  </Empleados>\n'
    xml += '</RDEP>'

    return xml
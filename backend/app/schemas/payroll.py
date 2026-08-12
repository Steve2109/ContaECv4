"""
ContaEC - Esquemas Pydantic de Nómina (Rol de Pago)
Schemas para generación, aprobación, pago y respuesta de roles de pago
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.hr_constants import ESTADOS_ROL


# ==========================================
# Generación de Rol de Pago
# ==========================================

class PayrollGenerate(BaseModel):
    """Esquema para generar un rol de pago mensual"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    periodo_mes: int = Field(
        ...,
        ge=1,
        le=12,
        description="Mes del período (1-12)",
        examples=[1],
    )
    periodo_anio: int = Field(
        ...,
        ge=2000,
        le=2100,
        description="Año del período",
        examples=[2024],
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones generales del rol",
    )


class PayrollDetalleExtras(BaseModel):
    """Esquema para ingresos/descuentos adicionales de un empleado en un rol"""
    employee_id: str = Field(..., description="ID del empleado")
    horas_extras_diurnas: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    horas_extras_nocturnas: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    horas_extras_dominicales: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    comisiones: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    bonos: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    otros_ingresos: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    anticipo: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    prestamo_empresa: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    retencion_judicial: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    otros_descuentos: Decimal = Field(default=Decimal("0.00"), decimal_places=2)


# ==========================================
# Décimo Tercero / Cuarto
# ==========================================

class DecimoTerceroRequest(BaseModel):
    """Esquema para calcular décimo tercero"""
    company_id: str = Field(..., description="ID de la empresa")
    periodo_anio: int = Field(..., ge=2000, le=2100, description="Año de cálculo")
    employee_id: str | None = Field(None, description="ID del empleado (opcional, todos si no se especifica)")


class DecimoCuartoRequest(BaseModel):
    """Esquema para calcular décimo cuarto"""
    company_id: str = Field(..., description="ID de la empresa")
    periodo_anio: int = Field(..., ge=2000, le=2100, description="Año de cálculo")
    region: str = Field(
        default="sierra",
        description="Región: sierra (pago agosto) o costa (pago marzo)",
    )
    employee_id: str | None = Field(None, description="ID del empleado (opcional)")

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        if v not in ("sierra", "costa"):
            raise ValueError("Región inválida. Válidas: sierra, costa")
        return v


# ==========================================
# Respuestas
# ==========================================

class RolPagoDetalleResponse(BaseModel):
    """Esquema de respuesta para un detalle del rol de pago"""
    id: UUID = Field(..., description="ID único del detalle")
    rol_pago_id: UUID = Field(..., description="ID del rol de pago")
    employee_id: UUID = Field(..., description="ID del empleado")

    # Ingresos
    sueldo_base: Decimal = Field(..., description="Sueldo base")
    horas_extras_diurnas: Decimal = Field(..., description="Horas extras diurnas")
    valor_horas_extras_diurnas: Decimal = Field(..., description="Valor horas extras diurnas")
    horas_extras_nocturnas: Decimal = Field(..., description="Horas extras nocturnas")
    valor_horas_extras_nocturnas: Decimal = Field(..., description="Valor horas extras nocturnas")
    horas_extras_dominicales: Decimal = Field(..., description="Horas extras dominicales")
    valor_horas_extras_dominicales: Decimal = Field(..., description="Valor horas extras dominicales")
    comisiones: Decimal = Field(..., description="Comisiones")
    bonos: Decimal = Field(..., description="Bonos")
    otros_ingresos: Decimal = Field(..., description="Otros ingresos")
    total_ingresos: Decimal = Field(..., description="Total ingresos")

    # Descuentos
    iess_personal_945: Decimal = Field(..., description="Aporte personal IESS 9.45%")
    anticipo: Decimal = Field(..., description="Anticipo")
    prestamo_empresa: Decimal = Field(..., description="Préstamo empresa")
    retencion_judicial: Decimal = Field(..., description="Retención judicial")
    otros_descuentos: Decimal = Field(..., description="Otros descuentos")
    total_descuentos: Decimal = Field(..., description="Total descuentos")

    # Aportes empleador
    iess_patronal_1115: Decimal = Field(..., description="Aporte patronal IESS 11.15%")
    iee_0005: Decimal = Field(..., description="IESS Riesgos 0.5%")
    secap_002: Decimal = Field(..., description="SECAP 0.2%")
    cenaces_001: Decimal = Field(..., description="CENACES 0.1%")
    total_aportes_empleador: Decimal = Field(..., description="Total aportes empleador")

    # Décimos
    decimo_tercero: Decimal = Field(..., description="Décimo tercero")
    decimo_cuarto: Decimal = Field(..., description="Décimo cuarto")

    # Vacaciones y fondo de reserva
    vacaciones_provision: Decimal = Field(..., description="Provisión vacaciones")
    fondos_reserva: Decimal = Field(..., description="Fondos de reserva")

    # Total
    liquido_recibir: Decimal = Field(..., description="Líquido a recibir")

    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class RolPagoResponse(BaseModel):
    """Esquema de respuesta para un rol de pago (cabecera)"""
    id: UUID = Field(..., description="ID único del rol")
    company_id: UUID = Field(..., description="ID de la empresa")
    user_id: UUID = Field(..., description="ID del usuario creador")
    periodo_mes: int = Field(..., description="Mes del período")
    periodo_anio: int = Field(..., description="Año del período")
    fecha_pago: datetime | None = Field(None, description="Fecha de pago")
    estado: str = Field(..., description="Estado del rol")
    total_remuneraciones: Decimal = Field(..., description="Total remuneraciones")
    total_descuentos: Decimal = Field(..., description="Total descuentos")
    total_empleador: Decimal = Field(..., description="Total aportes empleador")
    total_liquido: Decimal = Field(..., description="Total líquido")
    observaciones: str | None = Field(None, description="Observaciones")
    is_active: bool = Field(..., description="Activo en el sistema")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class RolPagoFullResponse(RolPagoResponse):
    """Esquema de respuesta para un rol de pago con detalles"""
    detalles: list[RolPagoDetalleResponse] = Field(
        default_factory=list,
        description="Detalles del rol por empleado",
    )


class DecimoResponse(BaseModel):
    """Esquema de respuesta para cálculo de décimos"""
    employee_id: str = Field(..., description="ID del empleado")
    cedula: str = Field(..., description="Cédula del empleado")
    nombre_completo: str = Field(..., description="Nombre completo")
    sueldo_mensual: Decimal = Field(..., description="Sueldo mensual")
    meses_trabajados: int = Field(..., description="Meses trabajados en el período")
    valor_decimo: Decimal = Field(..., description="Valor del décimo calculado")


class VacacionesBalanceResponse(BaseModel):
    """Esquema de respuesta para balance de vacaciones"""
    employee_id: str = Field(..., description="ID del empleado")
    cedula: str = Field(..., description="Cédula")
    nombre_completo: str = Field(..., description="Nombre completo")
    fecha_ingreso: datetime = Field(..., description="Fecha de ingreso")
    anios_servicio: int = Field(..., description="Años de servicio")
    dias_disponibles: Decimal = Field(..., description="Días disponibles")
    dias_acumulados: Decimal = Field(..., description="Días acumulados")
    valor_vacaciones: Decimal = Field(..., description="Valor monetario de vacaciones")


class FondosReservaResponse(BaseModel):
    """Esquema de respuesta para fondo de reserva"""
    employee_id: str = Field(..., description="ID del empleado")
    cedula: str = Field(..., description="Cédula")
    nombre_completo: str = Field(..., description="Nombre completo")
    fecha_ingreso: datetime = Field(..., description="Fecha de ingreso")
    anios_servicio: int = Field(..., description="Años de servicio")
    tiene_derecho: bool = Field(..., description="Tiene derecho a fondo de reserva")
    acumulado: Decimal = Field(..., description="Monto acumulado")


class IESSReportResponse(BaseModel):
    """Esquema de respuesta para reporte IESS"""
    company_id: str = Field(..., description="ID de la empresa")
    periodo_mes: int = Field(..., description="Mes del período")
    periodo_anio: int = Field(..., description="Año del período")
    total_empleados: int = Field(..., description="Total de empleados afiliados")
    total_aporte_personal: Decimal = Field(..., description="Total aporte personal")
    total_aporte_patronal: Decimal = Field(..., description="Total aporte patronal")
    total_aporte_iee: Decimal = Field(..., description="Total IEE riesgos")
    total_aporte_secap: Decimal = Field(..., description="Total SECAP")
    total_aporte_cenaces: Decimal = Field(..., description="Total CENACES")
    total_general: Decimal = Field(..., description="Total general aportes")
    detalle: list[dict] = Field(default_factory=list, description="Detalle por empleado")


class RDEPReportResponse(BaseModel):
    """Esquema de respuesta para reporte RDEP"""
    company_id: str = Field(..., description="ID de la empresa")
    periodo_mes: int = Field(..., description="Mes del período")
    periodo_anio: int = Field(..., description="Año del período")
    total_empleados: int = Field(..., description="Total de empleados")
    total_remuneraciones: Decimal = Field(..., description="Total remuneraciones")
    total_descuentos: Decimal = Field(..., description="Total descuentos")
    total_liquido: Decimal = Field(..., description="Total líquido pagado")
    total_aportes_empleador: Decimal = Field(..., description="Total aportes empleador")
    detalle: list[dict] = Field(default_factory=list, description="Detalle por empleado")

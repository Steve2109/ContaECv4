"""
ContaEC - Schemas de Contabilidad Core
Plan de Cuentas, Asientos Contables, Cuentas por Cobrar, Pagos, Períodos Fiscales
"""
from __future__ import annotations

from uuid import UUID

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# Plan de Cuentas
# ==========================================

class CuentaContableCreate(BaseModel):
    """Schema para crear una cuenta contable"""
    codigo: str = Field(..., max_length=20, description="Código de la cuenta (ej: 1.1.01.01)")
    nombre: str = Field(..., max_length=255, description="Nombre de la cuenta")
    tipo: str = Field(..., description="Tipo: activo, pasivo, patrimonio, ingreso, gasto, costo")
    naturaleza: str = Field(..., description="Naturaleza: deudora o acreedora")
    nivel: int = Field(default=1, description="Nivel jerárquico")
    cuenta_padre_id: str | None = None
    es_cuenta_movimiento: bool = True
    es_imputable: bool = True
    saldo_inicial: Decimal = Decimal("0")
    descripcion: str | None = None
    etiqueta: str | None = None
    notas: str | None = None
    cuenta_contrapartida_id: str | None = None


class CuentaContableUpdate(BaseModel):
    """Schema para actualizar una cuenta contable"""
    nombre: str | None = None
    tipo: str | None = None
    naturaleza: str | None = None
    nivel: int | None = None
    cuenta_padre_id: str | None = None
    es_cuenta_movimiento: bool | None = None
    es_imputable: bool | None = None
    saldo_inicial: Decimal | None = None
    descripcion: str | None = None
    etiqueta: str | None = None
    notas: str | None = None
    cuenta_contrapartida_id: str | None = None
    is_active: bool | None = None


class CuentaContableResponse(BaseModel):
    """Schema de respuesta de cuenta contable"""
    id: UUID
    company_id: UUID
    codigo: str
    nombre: str
    tipo: str
    naturaleza: str
    nivel: int
    cuenta_padre_id: UUID | None = None
    es_cuenta_movimiento: bool
    es_imputable: bool
    saldo_inicial: Decimal
    saldo_actual: Decimal
    total_debitos: Decimal
    total_creditos: Decimal
    descripcion: str | None = None
    etiqueta: str | None = None
    notas: str | None = None
    cuenta_contrapartida_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Computed
    codigo_nombre: str | None = None

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Asientos Contables
# ==========================================

class AsientoDetalleCreate(BaseModel):
    """Schema para crear un detalle de asiento"""
    cuenta_contable_id: str
    debito: Decimal = Decimal("0")
    credito: Decimal = Decimal("0")
    descripcion: str | None = None
    referencia_tipo: str | None = None
    referencia_id: str | None = None


class AsientoDetalleResponse(BaseModel):
    """Schema de respuesta de detalle de asiento"""
    id: UUID
    asiento_id: UUID
    cuenta_contable_id: UUID
    debito: Decimal
    credito: Decimal
    descripcion: str | None = None
    referencia_tipo: str | None = None
    referencia_id: UUID | None = None
    created_at: datetime
    # Cuenta contable info
    cuenta_codigo: str | None = None
    cuenta_nombre: str | None = None

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class AsientoContableCreate(BaseModel):
    """Schema para crear un asiento contable"""
    fecha: datetime
    tipo: str = Field(default="ordinario", description="Tipo: apertura, ordinario, cierre, ajuste, estimacion, reclasificacion")
    concepto: str = Field(..., max_length=500, description="Concepto del asiento")
    referencia_tipo: str | None = None
    referencia_id: str | None = None
    referencia_secuencial: str | None = None
    observaciones: str | None = None
    detalles: list[AsientoDetalleCreate] = Field(..., min_length=2, description="Al menos 2 líneas (débito y crédito)")
    periodo_fiscal_id: str | None = None


class AsientoContableUpdate(BaseModel):
    """Schema para actualizar un asiento contable (solo en borrador)"""
    concepto: str | None = None
    observaciones: str | None = None
    detalles: list[AsientoDetalleCreate] | None = None


class AsientoContableResponse(BaseModel):
    """Schema de respuesta de asiento contable"""
    id: UUID
    company_id: UUID
    user_id: UUID
    periodo_fiscal_id: UUID | None = None
    numero: str
    fecha: datetime
    tipo: str
    estado: str
    total_debitos: Decimal
    total_creditos: Decimal
    concepto: str
    referencia_tipo: str | None = None
    referencia_id: UUID | None = None
    referencia_secuencial: str | None = None
    observaciones: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    detalles: list[AsientoDetalleResponse] = []
    is_cuadrado: bool | None = None

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Cuentas por Cobrar
# ==========================================

class CuentaPorCobrarCreate(BaseModel):
    """Schema para crear una cuenta por cobrar"""
    client_id: str | None = None
    comprobante_id: str | None = None
    numero_factura: str | None = None
    fecha_emision: datetime
    fecha_vencimiento: datetime | None = None
    monto_total: Decimal
    dias_credito: int = 30
    cliente_nombre: str | None = None
    cliente_identificacion: str | None = None
    observaciones: str | None = None


class CuentaPorCobrarUpdate(BaseModel):
    """Schema para actualizar una cuenta por cobrar"""
    fecha_vencimiento: datetime | None = None
    dias_credito: int | None = None
    observaciones: str | None = None
    estado: str | None = None


class CuentaPorCobrarResponse(BaseModel):
    """Schema de respuesta de cuenta por cobrar"""
    id: UUID
    company_id: UUID
    client_id: UUID | None = None
    comprobante_id: UUID | None = None
    numero_factura: str | None = None
    fecha_emision: datetime
    fecha_vencimiento: datetime | None = None
    monto_total: Decimal
    monto_pagado: Decimal
    monto_pendiente: Decimal
    estado: str
    dias_credito: int
    dias_vencida: int
    cliente_nombre: str | None = None
    cliente_identificacion: str | None = None
    observaciones: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    rango_vencimiento: str | None = None

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Pagos / Cobros
# ==========================================

class PagoCreate(BaseModel):
    """Schema para crear un pago/cobro"""
    tipo: str = Field(..., description="Tipo: cobro, pago, otro")
    fecha: datetime
    monto: Decimal
    forma_pago: str = "01"
    referencia: str | None = None
    cuenta_bancaria_id: str | None = None
    cuenta_por_cobrar_id: str | None = None
    cuenta_por_pagar_id: str | None = None
    tercero_nombre: str | None = None
    tercero_identificacion: str | None = None
    observaciones: str | None = None


class PagoUpdate(BaseModel):
    """Schema para actualizar un pago"""
    forma_pago: str | None = None
    referencia: str | None = None
    observaciones: str | None = None
    estado: str | None = None


class PagoResponse(BaseModel):
    """Schema de respuesta de pago"""
    id: UUID
    company_id: UUID
    user_id: UUID
    tipo: str
    numero: str
    fecha: datetime
    monto: Decimal
    forma_pago: str
    referencia: str | None = None
    cuenta_bancaria_id: UUID | None = None
    cuenta_por_cobrar_id: UUID | None = None
    cuenta_por_pagar_id: UUID | None = None
    tercero_nombre: str | None = None
    tercero_identificacion: str | None = None
    estado: str
    observaciones: str | None = None
    asiento_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Períodos Fiscales
# ==========================================

class PeriodoFiscalCreate(BaseModel):
    """Schema para crear un período fiscal"""
    nombre: str = Field(..., max_length=100, description="Nombre del período")
    anio: int = Field(..., description="Año fiscal")
    mes: int | None = Field(None, ge=1, le=12, description="Mes (1-12, None para anual)")
    tipo_periodo: str = Field(default="mensual", description="Tipo: mensual, trimestral, semestral, anual")
    fecha_inicio: datetime
    fecha_fin: datetime
    observaciones: str | None = None


class PeriodoFiscalUpdate(BaseModel):
    """Schema para actualizar un período fiscal"""
    nombre: str | None = None
    observaciones: str | None = None


class PeriodoFiscalResponse(BaseModel):
    """Schema de respuesta de período fiscal"""
    id: UUID
    company_id: UUID
    nombre: str
    anio: int
    mes: int | None = None
    tipo_periodo: str
    fecha_inicio: datetime
    fecha_fin: datetime
    estado: str
    fecha_cierre: datetime | None = None
    cerrado_por: UUID | None = None
    total_debitos: Decimal
    total_creditos: Decimal
    total_asientos: int
    observaciones: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Reportes Contables
# ==========================================

class BalanceComprobacionItem(BaseModel):
    """Item del Balance de Comprobación"""
    codigo: str
    nombre: str
    tipo: str
    nivel: int
    saldo_deudor: Decimal = Decimal("0")
    saldo_acreedor: Decimal = Decimal("0")
    total_debitos: Decimal = Decimal("0")
    total_creditos: Decimal = Decimal("0")


class BalanceComprobacionResponse(BaseModel):
    """Respuesta del Balance de Comprobación"""
    items: list[BalanceComprobacionItem] = []
    total_debitos: Decimal = Decimal("0")
    total_creditos: Decimal = Decimal("0")
    total_saldo_deudor: Decimal = Decimal("0")
    total_saldo_acreedor: Decimal = Decimal("0")
    periodo: str | None = None
    fecha_generacion: datetime = Field(default_factory=datetime.now)


class LibroDiarioItem(BaseModel):
    """Item del Libro Diario"""
    asiento_numero: str
    asiento_fecha: datetime
    asiento_concepto: str
    asiento_tipo: str
    asiento_estado: str
    cuenta_codigo: str
    cuenta_nombre: str
    debito: Decimal = Decimal("0")
    credito: Decimal = Decimal("0")
    descripcion: str | None = None


class LibroMayorItem(BaseModel):
    """Item del Libro Mayor"""
    cuenta_codigo: str
    cuenta_nombre: str
    cuenta_tipo: str
    saldo_inicial: Decimal = Decimal("0")
    movimientos: list[dict] = []
    total_debitos: Decimal = Decimal("0")
    total_creditos: Decimal = Decimal("0")
    saldo_final: Decimal = Decimal("0")


class EnvejecimientoCarteraItem(BaseModel):
    """Item del envejecimiento de cartera (CxC)"""
    cliente_id: str | None = None
    cliente_nombre: str
    cliente_identificacion: str | None = None
    total: Decimal = Decimal("0")
    vigente: Decimal = Decimal("0")
    dias_1_30: Decimal = Decimal("0")
    dias_31_60: Decimal = Decimal("0")
    dias_61_90: Decimal = Decimal("0")
    dias_91_180: Decimal = Decimal("0")
    dias_mas_180: Decimal = Decimal("0")


class EnvejecimientoCarteraResponse(BaseModel):
    """Respuesta del envejecimiento de cartera"""
    items: list[EnvejecimientoCarteraItem] = []
    total_general: Decimal = Decimal("0")
    total_vigente: Decimal = Decimal("0")
    total_1_30: Decimal = Decimal("0")
    total_31_60: Decimal = Decimal("0")
    total_61_90: Decimal = Decimal("0")
    total_91_180: Decimal = Decimal("0")
    total_mas_180: Decimal = Decimal("0")


class ContabilidadStats(BaseModel):
    """Estadísticas del módulo contable"""
    total_cuentas: int = 0
    total_cuentas_activas: int = 0
    total_asientos: int = 0
    total_asientos_aprobados: int = 0
    total_cxc: int = 0
    total_cxc_pendiente: Decimal = Decimal("0")
    total_cxp_pendiente: Decimal = Decimal("0")
    total_cobros_mes: Decimal = Decimal("0")
    total_pagos_mes: Decimal = Decimal("0")
    periodos_abiertos: int = 0
    periodo_actual: str | None = None

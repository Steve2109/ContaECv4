"""
ContaEC - Schemas de Integraciones
Schemas para integracion bancaria y conectores e-commerce
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ========================================
# Cuenta Bancaria Schemas
# ========================================

class CuentaBancariaCreate(BaseModel):
    company_id: str
    nombre_banco: str = Field(..., min_length=1, max_length=200)
    codigo_banco: str | None = None
    tipo_cuenta: str = Field(default="corriente", pattern="^(ahorros|corriente)$")
    numero_cuenta: str = Field(..., min_length=1, max_length=50)
    iban: str | None = None
    swift_bic: str | None = None
    titular: str = Field(..., min_length=1, max_length=200)
    moneda: str = Field(default="USD", max_length=3)
    saldo_inicial: Decimal = Field(default=Decimal("0"))
    formato_extracto: str = Field(default="csv", pattern="^(csv|ofx|mt940|excel)$")
    configuracion_mapeo: str | None = None


class CuentaBancariaUpdate(BaseModel):
    nombre_banco: str | None = None
    codigo_banco: str | None = None
    tipo_cuenta: str | None = None
    numero_cuenta: str | None = None
    iban: str | None = None
    swift_bic: str | None = None
    titular: str | None = None
    moneda: str | None = None
    saldo_inicial: Decimal | None = None
    formato_extracto: str | None = None
    configuracion_mapeo: str | None = None
    is_active: bool | None = None


class CuentaBancariaResponse(BaseModel):
    id: UUID
    company_id: UUID
    nombre_banco: str
    codigo_banco: str | None
    tipo_cuenta: str
    numero_cuenta: str
    iban: str | None
    swift_bic: str | None
    titular: str
    moneda: str
    saldo_inicial: Decimal
    saldo_actual: Decimal
    ultima_fecha_sincronizacion: datetime | None
    formato_extracto: str
    configuracion_mapeo: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ========================================
# Extracto Bancario Schemas
# ========================================

class ExtractoBancarioCreate(BaseModel):
    company_id: str
    cuenta_bancaria_id: str
    fecha_desde: datetime
    fecha_hasta: datetime
    saldo_inicial: Decimal = Decimal("0")
    saldo_final: Decimal = Decimal("0")
    total_debitos: Decimal = Decimal("0")
    total_creditos: Decimal = Decimal("0")
    numero_movimientos: int = 0
    archivo_original: str | None = None
    notas: str | None = None


class ExtractoBancarioResponse(BaseModel):
    id: UUID
    company_id: UUID
    cuenta_bancaria_id: UUID
    fecha_desde: datetime
    fecha_hasta: datetime
    saldo_inicial: Decimal
    saldo_final: Decimal
    total_debitos: Decimal
    total_creditos: Decimal
    estado: str
    numero_movimientos: int
    movimientos_conciliados: int
    archivo_original: str | None
    notas: str | None
    created_at: datetime
    updated_at: datetime
    # Joined
    banco_nombre: str | None = None
    cuenta_numero: str | None = None

    model_config = {"from_attributes": True}


# ========================================
# Movimiento Bancario Schemas
# ========================================

class MovimientoBancarioCreate(BaseModel):
    company_id: str
    cuenta_bancaria_id: str
    extracto_id: str
    fecha: datetime
    tipo: str = Field(..., pattern="^(debito|credito)$")
    monto: Decimal = Field(..., gt=0)
    saldo_posterior: Decimal | None = None
    referencia: str | None = None
    descripcion: str | None = None
    beneficiario: str | None = None
    documento: str | None = None
    categoria: str | None = None


class MovimientoBancarioUpdate(BaseModel):
    conciliacion_estado: str | None = Field(None, pattern="^(pendiente|conciliado|ignorado)$")
    conciliacion_nota: str | None = None
    comprobante_id: str | None = None
    categoria: str | None = None


class MovimientoBancarioResponse(BaseModel):
    id: UUID
    company_id: UUID
    cuenta_bancaria_id: UUID
    extracto_id: UUID
    fecha: datetime
    tipo: str
    monto: Decimal
    saldo_posterior: Decimal | None
    referencia: str | None
    descripcion: str | None
    beneficiario: str | None
    documento: str | None
    conciliacion_estado: str
    conciliacion_fecha: datetime | None
    comprobante_id: UUID | None
    conciliacion_nota: str | None
    categoria: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ========================================
# E-Commerce Connector Schemas
# ========================================

class EcommerceConnectorCreate(BaseModel):
    company_id: str
    nombre: str = Field(..., min_length=1, max_length=200)
    plataforma: str = Field(
        ...,
        pattern="^(shopify|woocommerce|opencart|prestashop|magento|meli|otro)$",
    )
    url_tienda: str = Field(..., min_length=1, max_length=500)
    api_key: str | None = None
    api_secret: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    configuracion_extra: str | None = None
    sincronizacion_auto: bool = False
    frecuencia_sync: int = Field(default=60, ge=5)
    sync_productos: bool = True
    sync_ordenes: bool = True
    sync_clientes: bool = True
    sync_inventario: bool = True


class EcommerceConnectorUpdate(BaseModel):
    nombre: str | None = None
    url_tienda: str | None = None
    api_key: str | None = None
    api_secret: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    configuracion_extra: str | None = None
    sincronizacion_auto: bool | None = None
    frecuencia_sync: int | None = None
    sync_productos: bool | None = None
    sync_ordenes: bool | None = None
    sync_clientes: bool | None = None
    sync_inventario: bool | None = None
    is_active: bool | None = None


class EcommerceConnectorResponse(BaseModel):
    id: UUID
    company_id: UUID
    user_id: UUID
    nombre: str
    plataforma: str
    url_tienda: str
    api_key: str | None
    # api_secret intentionally excluded for security
    access_token: str | None
    # refresh_token intentionally excluded for security
    webhook_url: str | None
    configuracion_extra: str | None
    estado: str
    ultimo_error: str | None
    ultima_sincronizacion: datetime | None
    sincronizacion_auto: bool
    frecuencia_sync: int
    sync_productos: bool
    sync_ordenes: bool
    sync_clientes: bool
    sync_inventario: bool
    total_ordenes_sync: int
    total_productos_sync: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ========================================
# E-Commerce Sync Log Schemas
# ========================================

class EcommerceSyncLogCreate(BaseModel):
    company_id: str
    connector_id: str
    tipo_sync: str = Field(
        ...,
        pattern="^(productos|ordenes|clientes|inventario|completo)$",
    )
    creado_por: str | None = None


class EcommerceSyncLogResponse(BaseModel):
    id: UUID
    company_id: UUID
    connector_id: UUID
    tipo_sync: str
    estado: str
    fecha_inicio: datetime
    fecha_fin: datetime | None
    registros_procesados: int
    registros_creados: int
    registros_actualizados: int
    registros_errores: int
    detalle_errores: str | None
    resultado_resumen: str | None
    creado_por: UUID | None
    created_at: datetime
    # Joined
    connector_nombre: str | None = None
    connector_plataforma: str | None = None

    model_config = {"from_attributes": True}


# ========================================
# Integration Stats
# ========================================

class IntegrationStats(BaseModel):
    """Estadisticas generales de integraciones"""
    # Bank
    total_cuentas_bancarias: int = 0
    cuentas_activas: int = 0
    total_extractos: int = 0
    extractos_pendientes: int = 0
    movimientos_pendientes_conciliar: int = 0
    movimientos_conciliados: int = 0
    saldo_total_cuentas: Decimal = Decimal("0")
    # E-Commerce
    total_connectors: int = 0
    connectors_activos: int = 0
    connectors_por_plataforma: dict[str, int] = {}
    total_sync_logs: int = 0
    sync_logs_hoy: int = 0
    ultima_sync_fecha: datetime | None = None


# ==========================================
# E-Commerce Sync Responses (Fase 15)
# ==========================================

class EcommerceSyncProductsResponse(BaseModel):
    """Response for sync-products endpoint"""
    connector_id: str
    connector_nombre: str
    plataforma: str
    total_procesados: int = 0
    total_creados: int = 0
    total_actualizados: int = 0
    total_errores: int = 0
    errores: list[str] = Field(default_factory=list)
    sync_log_id: str | None = None


class EcommerceSyncOrdersResponse(BaseModel):
    """Response for sync-orders endpoint"""
    connector_id: str
    connector_nombre: str
    plataforma: str
    total_ordenes_procesadas: int = 0
    total_facturas_creadas: int = 0
    total_errores: int = 0
    errores: list[str] = Field(default_factory=list)
    sync_log_id: str | None = None


class EcommerceSyncInventoryResponse(BaseModel):
    """Response for sync-inventory endpoint"""
    connector_id: str
    connector_nombre: str
    plataforma: str
    total_productos_procesados: int = 0
    total_stock_actualizados: int = 0
    total_errores: int = 0
    errores: list[str] = Field(default_factory=list)
    sync_log_id: str | None = None


class EcommerceConnectorStatus(BaseModel):
    """Status response for e-commerce connector"""
    connector_id: str
    connector_nombre: str
    plataforma: str
    estado: str
    url_tienda: str
    ultima_sincronizacion: datetime | None = None
    ultimo_error: str | None = None
    total_productos_sync: int = 0
    total_ordenes_sync: int = 0
    is_active: bool
    sync_productos: bool
    sync_ordenes: bool
    sync_inventario: bool
    sync_clientes: bool
    ultima_sync_details: dict | None = None

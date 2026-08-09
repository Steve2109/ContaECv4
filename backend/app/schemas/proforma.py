"""
ContaEC - Schemas de Proforma
Pydantic models for request/response validation
"""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ============================================
# Detalle schemas
# ============================================

class ProformaDetalleCreate(BaseModel):
    """Schema para crear un detalle de proforma"""
    product_id: str | None = None
    codigo_principal: str
    codigo_auxiliar: str | None = None
    descripcion: str
    cantidad: Decimal = Field(gt=0)
    unidad_medida: str = "Unidad"
    precio_unitario: Decimal = Field(ge=0)
    descuento: Decimal = Field(ge=0, default=Decimal("0"))
    descuento_tipo: Literal["porcentaje", "dolares"] = Field(
        default="dolares",
        description="Tipo de descuento: 'porcentaje' (% del total de la línea) o 'dolares' (monto fijo)",
    )
    descuento_valor: Decimal | None = Field(
        None,
        ge=0,
        description="Valor bruto del descuento ingresado por el usuario (monto en dólares o porcentaje según descuento_tipo)",
    )
    iva_codigo: str = "4"
    iva_porcentaje: Decimal = Field(ge=0, default=Decimal("15"))
    ice_codigo: str | None = None
    ice_porcentaje: Decimal | None = None


class ProformaDetalleResponse(BaseModel):
    """Schema de respuesta para un detalle de proforma"""
    id: str
    product_id: str | None = None
    codigo_principal: str
    codigo_auxiliar: str | None = None
    descripcion: str
    cantidad: Decimal
    unidad_medida: str
    precio_unitario: Decimal
    descuento: Decimal
    precio_total_sin_impuestos: Decimal
    iva_codigo: str
    iva_porcentaje: Decimal
    iva_valor: Decimal
    ice_codigo: str | None = None
    ice_porcentaje: Decimal | None = None
    ice_valor: Decimal | None = None

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ============================================
# Proforma schemas
# ============================================

class ProformaCreate(BaseModel):
    """Schema para crear una proforma"""
    company_id: str
    client_id: str | None = None
    detalles: list[ProformaDetalleCreate] = Field(min_length=1)
    observaciones: str | None = None
    forma_pago: str | None = "01"
    fecha_validez: str | None = None  # ISO date string
    info_adicional: dict[str, str] | None = None


class ProformaUpdate(BaseModel):
    """Schema para actualizar una proforma (solo BORRADOR)"""
    client_id: str | None = None
    detalles: list[ProformaDetalleCreate] | None = None
    observaciones: str | None = None
    forma_pago: str | None = None
    fecha_validez: str | None = None
    info_adicional: dict[str, str] | None = None


class ProformaResponse(BaseModel):
    """Schema de respuesta completa de una proforma"""
    id: str
    company_id: str
    client_id: str | None = None
    secuencial: str
    fecha_emision: datetime
    fecha_validez: datetime | None = None
    estado: str
    cliente_tipo_identificacion: str
    cliente_identificacion: str
    cliente_razon_social: str
    cliente_direccion: str | None = None
    cliente_email: str | None = None
    cliente_telefono: str | None = None
    subtotal_sin_impuestos: Decimal
    subtotal_iva_0: Decimal = Decimal("0")
    subtotal_iva_5: Decimal = Decimal("0")
    subtotal_iva_8: Decimal = Decimal("0")
    subtotal_iva_12: Decimal = Decimal("0")
    subtotal_iva_13: Decimal = Decimal("0")
    subtotal_iva_14: Decimal = Decimal("0")
    subtotal_iva_15: Decimal = Decimal("0")
    subtotal_no_objeto_iva: Decimal = Decimal("0")
    subtotal_exento_iva: Decimal = Decimal("0")
    total_iva: Decimal
    total_ice: Decimal
    total_descuento: Decimal
    total_con_impuestos: Decimal
    forma_pago: str | None = None
    observaciones: str | None = None
    comprobante_convertido_id: str | None = None
    detalles: list[ProformaDetalleResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ProformaListResponse(BaseModel):
    """Schema de respuesta resumida para listado de proformas"""
    id: str
    secuencial: str
    fecha_emision: datetime
    fecha_validez: datetime | None = None
    estado: str
    cliente_razon_social: str
    total_con_impuestos: Decimal
    comprobante_convertido_id: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ProformaStatsResponse(BaseModel):
    """Schema de estadísticas de proformas"""
    total: int
    borrador: int
    enviada: int
    aceptada: int
    rechazada: int
    convertida: int

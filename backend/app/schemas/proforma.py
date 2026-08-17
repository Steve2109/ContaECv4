"""
ContaEC - Schemas de Proforma
Pydantic models for request/response validation
"""
import json
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    id: UUID
    product_id: UUID | None = None
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
    propina: Decimal | None = Field(
        None,
        ge=0,
        description="Propina (monto fijo en dólares) que se suma al total",
    )


class ProformaUpdate(BaseModel):
    """Schema para actualizar una proforma (solo BORRADOR/CERRADA)"""
    client_id: str | None = None
    detalles: list[ProformaDetalleCreate] | None = None
    observaciones: str | None = None
    forma_pago: str | None = None
    fecha_validez: str | None = None
    info_adicional: dict[str, str] | None = None
    propina: Decimal | None = Field(
        None,
        ge=0,
        description="Propina (monto fijo en dólares) que se suma al total",
    )


class ProformaResponse(BaseModel):
    """Schema de respuesta completa de una proforma"""
    id: UUID
    company_id: UUID
    client_id: UUID | None = None
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
    propina: Decimal = Decimal("0")
    info_adicional: dict[str, str] | None = None
    comprobante_convertido_id: UUID | None = None
    detalles: list[ProformaDetalleResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @field_validator("info_adicional", mode="before")
    @classmethod
    def _parse_info_adicional(cls, v):
        """El modelo guarda info_adicional como JSON string; se devuelve como dict"""
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except Exception:
                return None
        return v

    @model_validator(mode="after")
    def _compute_propina(self):
        """Propina derivada de info_adicional (no hay columna propia en BD)"""
        try:
            if self.info_adicional and "propina" in self.info_adicional:
                self.propina = Decimal(str(self.info_adicional["propina"]))
        except Exception:
            self.propina = Decimal("0")
        return self


class ProformaListResponse(BaseModel):
    """Schema de respuesta resumida para listado de proformas"""
    id: UUID
    secuencial: str
    fecha_emision: datetime
    fecha_validez: datetime | None = None
    estado: str
    cliente_razon_social: str
    total_con_impuestos: Decimal
    comprobante_convertido_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ProformaStatsResponse(BaseModel):
    """Schema de estadísticas de proformas"""
    total: int
    borrador: int
    cerrada: int = 0
    enviada: int
    aceptada: int
    rechazada: int
    convertida: int

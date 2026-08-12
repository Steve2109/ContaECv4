"""
ContaEC - Esquemas Pydantic de Comprobante Electrónico
Schemas para creación, actualización y respuesta de comprobantes y detalles
según la Ficha Técnica v2.32 del SRI (Ecuador)

Estados del comprobante:
- Internos: borrador, firmado, enviado
- SRI: autorizado, rechazado, devuelto, caducado, anulado, contingencia
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================
# Estados del Comprobante
# ==========================================

class ComprobanteEstadoEnum(str, Enum):
    """
    Estados posibles del comprobante electrónico.
    Combina estados internos y estados del SRI.
    """
    # Estados internos (pre-envío)
    BORRADOR = "borrador"           # Borrador - aún no procesado
    FIRMADO = "firmado"             # Firmado digitalmente, pendiente de envío
    ENVIADO = "enviado"             # Enviado al SRI, pendiente respuesta

    # Estados SRI
    AUTORIZADO = "autorizado"       # Autorizado por el SRI
    RECHAZADO = "rechazado"         # Rechazado por el SRI
    DEVUELTO = "devuelto"           # Devuelto por el SRI para corrección
    CADUCADO = "caducado"           # Caducado (excedió tiempo de autorización)
    ANULADO = "anulado"             # Anulado por el emisor
    CONTINGENCIA = "contingencia"   # Generado en modo contingencia

    # Equivalentes SRI (siglas)
    PPR = "ppr"                     # En procesamiento (SRI)
    NAT = "nat"                     # No autorizado (SRI)


def estado_to_sigla(estado: str) -> str:
    """
    Convierte un estado a su sigla SRI equivalente.

    Args:
        estado: Estado del comprobante (ej: "autorizado", "borrador")

    Returns:
        Sigla SRI (ej: "AUT", "PPR") o None si no tiene equivalente
    """
    mapeo = {
        "borrador": None,           # No tiene equivalente SRI
        "firmado": None,            # No tiene equivalente SRI
        "enviado": "PPR",           # En procesamiento
        "autorizado": "AUT",
        "rechazado": "NAT",
        "devuelto": "DEV",
        "devuelta": "DEV",
        "caducado": "CAD",
        "caducada": "CAD",
        "anulado": "ANU",
        "anulada": "ANU",
        "contingencia": "CON",
        "ppr": "PPR",
        "nat": "NAT",
    }
    return mapeo.get(estado.lower())


def sigla_to_estado(sigla: str) -> str:
    """
    Convierte una sigla SRI a estado interno.

    Args:
        sigla: Sigla SRI (ej: "AUT", "PPR")

    Returns:
        Estado interno (ej: "autorizado", "ppr")
    """
    mapeo = {
        "PPR": "enviado",
        "AUT": "autorizado",
        "NAT": "rechazado",
        "DEV": "devuelto",
        "CAD": "caducado",
        "ANU": "anulado",
        "CON": "contingencia",
    }
    return mapeo.get(sigla, sigla.lower())


# ==========================================
# Esquemas de Detalle (líneas del comprobante)
# ==========================================

class ComprobanteDetalleCreate(BaseModel):
    """Esquema para crear una línea de detalle del comprobante"""
    product_id: str | None = Field(
        None,
        description="ID del producto (FK opcional al catálogo de productos)",
    )
    codigo_principal: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código principal del bien o servicio",
        examples=["PROD001"],
    )
    codigo_auxiliar: str | None = Field(
        None,
        max_length=50,
        description="Código auxiliar del bien o servicio",
    )
    descripcion: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Descripción del bien o servicio",
        examples=["Servicio de consultoría"],
    )
    cantidad: Decimal = Field(
        ...,
        gt=0,
        description="Cantidad del bien o servicio (hasta 6 decimales)",
        examples=["1.000000"],
    )
    unidad_medida: str = Field(
        default="Unidad",
        max_length=50,
        description="Unidad de medida (ej: Unidad, Kilogramo, Litro, Horas)",
    )
    precio_unitario: Decimal = Field(
        ...,
        gt=0,
        description="Precio unitario sin impuestos",
        examples=["100.00"],
    )
    descuento: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Monto de descuento aplicado al detalle (resultado final en dólares)",
    )
    descuento_tipo: Literal["porcentaje", "dolares"] = Field(
        default="dolares",
        description="Tipo de descuento: 'porcentaje' (% del total de la línea) o 'dolares' (monto fijo)",
    )
    descuento_valor: Decimal | None = Field(
        None,
        ge=0,
        description="Valor bruto del descuento ingresado por el usuario (monto en dólares o porcentaje según descuento_tipo)",
    )
    iva_codigo: str = Field(
        default="4",
        min_length=1,
        max_length=2,
        description="Código de tarifa de IVA según Tabla 16 del SRI (4=15% default, 10=13%, 2=12%, etc)",
        examples=["4"],
    )
    iva_porcentaje: Decimal = Field(
        default=Decimal("15.00"),
        ge=0,
        description="Porcentaje de IVA (default 15%, también: 0, 5, 8, 12, 13, 14)",
        examples=["15.00"],
    )
    ice_codigo: str | None = Field(
        None,
        max_length=3,
        description="Código de tarifa de ICE según Tabla 18 del SRI",
    )
    ice_porcentaje: Decimal | None = Field(
        None,
        ge=0,
        description="Porcentaje de ICE (si aplica)",
    )


class ComprobanteDetalleResponse(BaseModel):
    """Esquema de respuesta para una línea de detalle del comprobante"""
    id: UUID = Field(..., description="ID único del detalle")
    product_id: UUID | None = Field(None, description="ID del producto")
    codigo_principal: str = Field(..., description="Código principal")
    codigo_auxiliar: str | None = Field(None, description="Código auxiliar")
    descripcion: str = Field(..., description="Descripción del bien/servicio")
    cantidad: Decimal = Field(..., description="Cantidad")
    unidad_medida: str = Field(..., description="Unidad de medida")
    precio_unitario: Decimal = Field(..., description="Precio unitario sin impuestos")
    descuento: Decimal = Field(..., description="Monto de descuento")
    precio_total_sin_impuestos: Decimal = Field(..., description="Total sin impuestos")
    iva_codigo: str = Field(..., description="Código de tarifa IVA")
    iva_porcentaje: Decimal = Field(..., description="Porcentaje de IVA")
    iva_valor: Decimal = Field(..., description="Valor del IVA calculado")
    ice_codigo: str | None = Field(None, description="Código de tarifa ICE")
    ice_porcentaje: Decimal | None = Field(None, description="Porcentaje de ICE")
    ice_valor: Decimal | None = Field(None, description="Valor del ICE calculado")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Esquemas de Comprobante
# ==========================================

class ComprobanteCreate(BaseModel):
    """Esquema para crear un nuevo comprobante electrónico"""
    company_id: str = Field(
        ...,
        description="ID de la empresa emisora del comprobante",
    )
    client_id: str = Field(
        ...,
        description="ID del cliente/comprador",
    )
    tipo_comprobante: str = Field(
        ...,
        description="Código de tipo de comprobante según Tabla 1 del SRI (01, 03, 04, 05, 06, 07)",
        examples=["01"],
    )
    forma_pago: str = Field(
        default="01",
        max_length=2,
        description="Código de forma de pago según Tabla 23 del SRI",
        examples=["01"],
    )
    detalles: list[ComprobanteDetalleCreate] = Field(
        ...,
        min_length=1,
        description="Lista de líneas de detalle del comprobante",
    )
    # Para Notas de Crédito/Débito
    comprobante_modificado_id: str | None = Field(
        None,
        description="ID del comprobante que se modifica (para NC/ND)",
    )
    motivo_modificacion: str | None = Field(
        None,
        max_length=500,
        description="Motivo de la modificación del comprobante",
    )
    # Para retenciones
    retencion_iva_codigo: str | None = Field(
        None,
        max_length=2,
        description="Código de retención de IVA según Tabla 19 del SRI",
    )
    retencion_iva_porcentaje: Decimal | None = Field(
        None,
        ge=0,
        description="Porcentaje de retención de IVA",
    )
    retencion_renta_codigo: str | None = Field(
        None,
        max_length=3,
        description="Código de retención de Renta según Tabla 20 del SRI",
    )
    retencion_renta_porcentaje: Decimal | None = Field(
        None,
        ge=0,
        description="Porcentaje de retención de Renta",
    )
    # Info adicional
    info_adicional: dict[str, str] | None = Field(
        None,
        description="Información adicional como pares clave-valor para campoAdicional del SRI",
        examples=[{"email": "cliente@email.com", "telefono": "0991234567"}],
    )

    @field_validator("tipo_comprobante")
    @classmethod
    def validate_tipo_comprobante(cls, v: str) -> str:
        """Valida que el tipo de comprobante sea válido según Tabla 1 del SRI"""
        validos = {"01", "03", "04", "05", "06", "07"}
        if v not in validos:
            raise ValueError(
                f"Tipo de comprobante inválido: {v}. "
                f"Válidos: 01 (Factura), 03 (Liquidación), 04 (NC), 05 (ND), 06 (Guía), 07 (Retención)"
            )
        return v

    @field_validator("forma_pago")
    @classmethod
    def validate_forma_pago(cls, v: str) -> str:
        """Valida que la forma de pago sea válida según Tabla 23 del SRI"""
        validos = {"01", "15", "16", "17", "18", "19", "20", "21"}
        if v not in validos:
            raise ValueError(
                f"Forma de pago inválida: {v}. "
                f"Válidos: 01, 15, 16, 17, 18, 19, 20, 21"
            )
        return v

    @field_validator("detalles")
    @classmethod
    def validate_detalles_not_empty(cls, v: list) -> list:
        """Valida que haya al menos un detalle"""
        if not v or len(v) == 0:
            raise ValueError("El comprobante debe tener al menos un detalle")
        return v


class ComprobanteResponse(BaseModel):
    """Esquema de respuesta para un comprobante electrónico completo"""
    id: UUID = Field(..., description="ID único del comprobante")
    company_id: UUID = Field(..., description="ID de la empresa emisora")
    client_id: UUID | None = Field(None, description="ID del cliente")
    tipo_comprobante: str = Field(..., description="Código de tipo de comprobante")
    secuencial: str = Field(..., description="Número secuencial (9 dígitos)")
    clave_acceso: str | None = Field(None, description="Clave de acceso SRI (49 dígitos)")
    fecha_emision: datetime = Field(..., description="Fecha y hora de emisión")
    estado: str = Field(..., description="Estado del comprobante")
    ambiente: str = Field(..., description="Tipo de ambiente: 1=Pruebas, 2=Producción")
    # Información del cliente (desnormalizada)
    cliente_tipo_identificacion: str | None = Field(None, description="Tipo de identificación del cliente")
    cliente_identificacion: str | None = Field(None, description="Número de identificación del cliente")
    cliente_razon_social: str | None = Field(None, description="Razón social del cliente")
    # Totales
    subtotal_sin_impuestos: Decimal = Field(..., description="Subtotal sin impuestos")
    subtotal_iva_0: Decimal = Field(default=Decimal("0"), description="Subtotal con IVA 0%")
    subtotal_iva_5: Decimal = Field(default=Decimal("0"), description="Subtotal con IVA 5%")
    subtotal_iva_8: Decimal = Field(default=Decimal("0"), description="Subtotal con IVA 8%")
    subtotal_iva_12: Decimal = Field(default=Decimal("0"), description="Subtotal con IVA 12%")
    subtotal_iva_13: Decimal = Field(default=Decimal("0"), description="Subtotal con IVA 13%")
    subtotal_iva_14: Decimal = Field(default=Decimal("0"), description="Subtotal con IVA 14%")
    subtotal_iva_15: Decimal = Field(default=Decimal("0"), description="Subtotal con IVA 15%")
    subtotal_no_objeto_iva: Decimal = Field(default=Decimal("0"), description="Subtotal no objeto de IVA")
    subtotal_exento_iva: Decimal = Field(default=Decimal("0"), description="Subtotal exento de IVA")
    total_iva: Decimal = Field(..., description="Total del IVA")
    total_ice: Decimal = Field(..., description="Total del ICE")
    total_descuento: Decimal = Field(..., description="Total de descuentos")
    total_con_impuestos: Decimal = Field(..., description="Total con impuestos (gran total)")
    # SRI
    numero_autorizacion: str | None = Field(None, description="Número de autorización del SRI")
    fecha_autorizacion: datetime | None = Field(None, description="Fecha de autorización del SRI")
    sri_mensaje: str | None = Field(None, description="Mensaje de respuesta del SRI")
    # Detalles
    detalles: list[ComprobanteDetalleResponse] = Field(..., description="Líneas de detalle")
    # Timestamps
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ComprobanteListResponse(BaseModel):
    """Esquema ligero para listar comprobantes"""
    id: UUID = Field(..., description="ID único del comprobante")
    tipo_comprobante: str = Field(..., description="Código de tipo de comprobante")
    secuencial: str = Field(..., description="Número secuencial")
    clave_acceso: str | None = Field(None, description="Clave de acceso SRI")
    fecha_emision: datetime = Field(..., description="Fecha de emisión")
    estado: str = Field(..., description="Estado del comprobante")
    cliente_razon_social: str | None = Field(None, description="Razón social del cliente")
    total_con_impuestos: Decimal = Field(..., description="Total con impuestos")
    numero_autorizacion: str | None = Field(None, description="Número de autorización SRI")
    created_at: datetime = Field(..., description="Fecha de creación")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class ComprobanteStatsResponse(BaseModel):
    """Estadísticas de comprobantes para el dashboard"""
    total: int = Field(..., description="Total de comprobantes")
    borrador: int = Field(..., description="Comprobantes en borrador")
    firmado: int = Field(..., description="Comprobantes firmados")
    enviado: int = Field(..., description="Comprobantes enviados al SRI")
    autorizado: int = Field(..., description="Comprobantes autorizados por el SRI")
    rechazado: int = Field(..., description="Comprobantes rechazados por el SRI")
    total_amount: Decimal = Field(..., description="Monto total de comprobantes autorizados")


class CorreccionRequest(BaseModel):
    """Esquema para corregir un comprobante rechazado"""
    detalles: list[ComprobanteDetalleCreate] | None = Field(
        None,
        description="Nuevos detalles del comprobante (reemplaza los existentes)",
    )
    info_adicional: dict[str, str] | None = Field(
        None,
        description="Información adicional actualizada",
    )
    forma_pago: str | None = Field(
        None,
        max_length=2,
        description="Código de forma de pago actualizado",
    )
    motivo_modificacion: str | None = Field(
        None,
        max_length=500,
        description="Motivo de la corrección",
    )

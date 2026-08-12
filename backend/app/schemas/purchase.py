"""
ContaEC - Esquemas Pydantic de Compras
Schemas para órdenes de compra, recepciones de mercadería,
cuentas por pagar y retenciones de compra
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# Orden de Compra
# ==========================================

class OrdenCompraDetalleCreate(BaseModel):
    """Esquema para crear una línea de detalle de orden de compra"""
    product_id: str | None = Field(
        None,
        description="ID del producto (FK opcional al catálogo)",
    )
    codigo_principal: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código principal del bien o servicio",
        examples=["PROD001"],
    )
    descripcion: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Descripción del bien o servicio",
        examples=["Materia prima para producción"],
    )
    cantidad: Decimal = Field(
        ...,
        gt=0,
        description="Cantidad solicitada",
        examples=["100.0000"],
    )
    precio_unitario: Decimal = Field(
        ...,
        gt=0,
        description="Precio unitario sin impuestos",
        examples=["50.00"],
    )
    iva_codigo: str = Field(
        ...,
        max_length=2,
        description="Código de tarifa de IVA según Tabla 16 del SRI",
        examples=["10"],
    )
    iva_porcentaje: Decimal = Field(
        ...,
        ge=0,
        description="Porcentaje de IVA",
        examples=["13.00"],
    )
    descuento: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Monto de descuento",
    )


class OrdenCompraDetalleResponse(BaseModel):
    """Esquema de respuesta para una línea de detalle de orden de compra"""
    id: UUID = Field(..., description="ID único del detalle")
    orden_compra_id: UUID = Field(..., description="ID de la orden de compra")
    product_id: UUID | None = Field(None, description="ID del producto")
    codigo_principal: str = Field(..., description="Código principal")
    descripcion: str = Field(..., description="Descripción")
    cantidad: Decimal = Field(..., description="Cantidad solicitada")
    cantidad_recibida: Decimal = Field(..., description="Cantidad recibida")
    precio_unitario: Decimal = Field(..., description="Precio unitario")
    iva_codigo: str = Field(..., description="Código de tarifa IVA")
    iva_porcentaje: Decimal = Field(..., description="Porcentaje de IVA")
    descuento: Decimal = Field(..., description="Monto de descuento")
    precio_total: Decimal = Field(..., description="Precio total")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class OrdenCompraCreate(BaseModel):
    """Esquema para crear una nueva orden de compra"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    supplier_id: str = Field(
        ...,
        description="ID del proveedor",
    )
    fecha_emision: datetime = Field(
        ...,
        description="Fecha de emisión de la orden",
    )
    fecha_entrega_estimada: datetime | None = Field(
        None,
        description="Fecha estimada de entrega",
    )
    detalles: list[OrdenCompraDetalleCreate] = Field(
        ...,
        min_length=1,
        description="Lista de líneas de detalle",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales",
    )


class OrdenCompraUpdate(BaseModel):
    """Esquema para actualizar una orden de compra"""
    fecha_entrega_estimada: datetime | None = Field(
        None,
        description="Fecha estimada de entrega",
    )
    estado: str | None = Field(
        None,
        max_length=20,
        description="Estado: borrador, enviada, parcial, recibida, anulada",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales",
    )


class OrdenCompraResponse(BaseModel):
    """Esquema de respuesta para una orden de compra"""
    id: UUID = Field(..., description="ID único de la orden de compra")
    company_id: UUID = Field(..., description="ID de la empresa")
    supplier_id: UUID = Field(..., description="ID del proveedor")
    user_id: UUID = Field(..., description="ID del usuario creador")
    numero: str = Field(..., description="Número de orden de compra")
    fecha_emision: datetime = Field(..., description="Fecha de emisión")
    fecha_entrega_estimada: datetime | None = Field(None, description="Fecha estimada de entrega")
    estado: str = Field(..., description="Estado de la orden")
    subtotal_sin_impuestos: Decimal = Field(..., description="Subtotal sin impuestos")
    total_iva: Decimal = Field(..., description="Total del IVA")
    total_con_impuestos: Decimal = Field(..., description="Total con impuestos")
    observaciones: str | None = Field(None, description="Observaciones")
    is_active: bool = Field(..., description="Está activa")
    detalles: list[OrdenCompraDetalleResponse] = Field(..., description="Líneas de detalle")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Recepción de Mercadería
# ==========================================

class RecepcionMercaderiaDetalleCreate(BaseModel):
    """Esquema para crear una línea de detalle de recepción de mercadería"""
    product_id: str | None = Field(
        None,
        description="ID del producto (FK opcional)",
    )
    orden_compra_detalle_id: str | None = Field(
        None,
        description="ID del detalle de orden de compra asociado",
    )
    codigo_principal: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código principal del bien o servicio",
    )
    descripcion: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Descripción del bien o servicio",
    )
    cantidad_recibida: Decimal = Field(
        ...,
        gt=0,
        description="Cantidad recibida",
    )
    cantidad_dañada: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Cantidad dañada o defectuosa",
    )
    precio_unitario: Decimal = Field(
        ...,
        gt=0,
        description="Precio unitario sin impuestos",
    )


class RecepcionMercaderiaDetalleResponse(BaseModel):
    """Esquema de respuesta para una línea de detalle de recepción"""
    id: UUID = Field(..., description="ID único del detalle")
    recepcion_id: UUID = Field(..., description="ID de la recepción")
    product_id: UUID | None = Field(None, description="ID del producto")
    orden_compra_detalle_id: UUID | None = Field(None, description="ID del detalle de OC")
    codigo_principal: str = Field(..., description="Código principal")
    descripcion: str = Field(..., description="Descripción")
    cantidad_recibida: Decimal = Field(..., description="Cantidad recibida")
    cantidad_dañada: Decimal = Field(..., description="Cantidad dañada")
    precio_unitario: Decimal = Field(..., description="Precio unitario")
    precio_total: Decimal = Field(..., description="Precio total")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class RecepcionMercaderiaCreate(BaseModel):
    """Esquema para crear una nueva recepción de mercadería"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    orden_compra_id: str | None = Field(
        None,
        description="ID de la orden de compra asociada (opcional)",
    )
    supplier_id: str = Field(
        ...,
        description="ID del proveedor",
    )
    fecha_recepcion: datetime = Field(
        ...,
        description="Fecha de recepción de la mercadería",
    )
    detalles: list[RecepcionMercaderiaDetalleCreate] = Field(
        ...,
        min_length=1,
        description="Lista de líneas de detalle",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales",
    )


class RecepcionMercaderiaUpdate(BaseModel):
    """Esquema para actualizar una recepción de mercadería"""
    estado: str | None = Field(
        None,
        max_length=20,
        description="Estado: pendiente, conformada, rechazada",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales",
    )


class RecepcionMercaderiaResponse(BaseModel):
    """Esquema de respuesta para una recepción de mercadería"""
    id: UUID = Field(..., description="ID único de la recepción")
    company_id: UUID = Field(..., description="ID de la empresa")
    orden_compra_id: UUID | None = Field(None, description="ID de la orden de compra")
    supplier_id: UUID = Field(..., description="ID del proveedor")
    user_id: UUID = Field(..., description="ID del usuario")
    numero: str = Field(..., description="Número de recepción")
    fecha_recepcion: datetime = Field(..., description="Fecha de recepción")
    estado: str = Field(..., description="Estado")
    observaciones: str | None = Field(None, description="Observaciones")
    is_active: bool = Field(..., description="Está activa")
    detalles: list[RecepcionMercaderiaDetalleResponse] = Field(..., description="Líneas de detalle")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Cuenta por Pagar
# ==========================================

class CuentaPorPagarCreate(BaseModel):
    """Esquema para crear una nueva cuenta por pagar"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    supplier_id: str = Field(
        ...,
        description="ID del proveedor",
    )
    comprobante_id: str | None = Field(
        None,
        description="ID del comprobante electrónico asociado",
    )
    orden_compra_id: str | None = Field(
        None,
        description="ID de la orden de compra asociada",
    )
    numero_factura: str | None = Field(
        None,
        max_length=20,
        description="Número de factura del proveedor",
    )
    fecha_emision: datetime = Field(
        ...,
        description="Fecha de emisión de la factura",
    )
    fecha_vencimiento: datetime | None = Field(
        None,
        description="Fecha de vencimiento del pago",
    )
    monto_total: Decimal = Field(
        ...,
        gt=0,
        description="Monto total de la factura",
    )
    dias_credito: int = Field(
        default=0,
        ge=0,
        description="Días de crédito concedidos",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales",
    )


class CuentaPorPagarUpdate(BaseModel):
    """Esquema para actualizar una cuenta por pagar"""
    monto_pagado: Decimal | None = Field(
        None,
        ge=0,
        description="Monto pagado adicional",
    )
    estado: str | None = Field(
        None,
        max_length=20,
        description="Estado: pendiente, parcial, pagada, vencida, anulada",
    )
    fecha_vencimiento: datetime | None = Field(
        None,
        description="Fecha de vencimiento del pago",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales",
    )


class CuentaPorPagarResponse(BaseModel):
    """Esquema de respuesta para una cuenta por pagar"""
    id: UUID = Field(..., description="ID único de la cuenta por pagar")
    company_id: UUID = Field(..., description="ID de la empresa")
    supplier_id: UUID = Field(..., description="ID del proveedor")
    user_id: UUID = Field(..., description="ID del usuario")
    comprobante_id: UUID | None = Field(None, description="ID del comprobante")
    orden_compra_id: UUID | None = Field(None, description="ID de la orden de compra")
    numero_factura: str | None = Field(None, description="Número de factura")
    fecha_emision: datetime = Field(..., description="Fecha de emisión")
    fecha_vencimiento: datetime | None = Field(None, description="Fecha de vencimiento")
    monto_total: Decimal = Field(..., description="Monto total")
    monto_pagado: Decimal = Field(..., description="Monto pagado")
    monto_pendiente: Decimal = Field(..., description="Monto pendiente")
    estado: str = Field(..., description="Estado")
    dias_credito: int = Field(..., description="Días de crédito")
    observaciones: str | None = Field(None, description="Observaciones")
    is_active: bool = Field(..., description="Está activa")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class CuentaPorPagarPayment(BaseModel):
    """Esquema para registrar un pago parcial o total"""
    monto: Decimal = Field(
        ...,
        gt=0,
        description="Monto a pagar",
    )
    metodo_pago: str | None = Field(
        None,
        max_length=50,
        description="Forma de pago (transferencia, cheque, efectivo, etc.)",
    )
    referencia: str | None = Field(
        None,
        max_length=50,
        description="Número de referencia del pago",
    )
    observaciones: str | None = Field(
        None,
        description="Notas adicionales sobre el pago",
    )


class CuentaPorPagarRenegotiation(BaseModel):
    """Esquema para renegociar los plazos de pago"""
    nueva_fecha_vencimiento: datetime | None = Field(
        None,
        description="Nueva fecha de vencimiento",
    )
    dias_extension: int | None = Field(
        None,
        gt=0,
        description="Días a extender desde la fecha de vencimiento actual",
    )
    motivo: str | None = Field(
        None,
        max_length=500,
        description="Motivo de la renegociación",
    )


class CuentaPorPagarSummary(BaseModel):
    """Esquema de resumen de cuentas por pagar"""
    total_pendiente: Decimal = Field(..., description="Total pendiente (saldo pendiente de cuentas activas)")
    total_vencidas: Decimal = Field(..., description="Total de cuentas vencidas (saldo pendiente)")
    total_proximas_a_vencer: Decimal = Field(..., description="Total próximo a vencer (dentro de dias_proximos días)")
    cuentas_por_estado: dict[str, int] = Field(
        default_factory=dict,
        description="Cantidad de cuentas agrupadas por estado",
    )
    total_cuentas: int = Field(..., description="Total de cuentas pendientes/parciales/vencidas")
    dias_proximos: int = Field(..., description="Días usados para calcular 'próximo a vencer'")
    generado_en: datetime = Field(..., description="Fecha de generación del resumen")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Retención de Compra
# ==========================================

class RetencionCompraCreate(BaseModel):
    """Esquema para crear una nueva retención de compra"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    supplier_id: str = Field(
        ...,
        description="ID del proveedor",
    )
    cuenta_por_pagar_id: str | None = Field(
        None,
        description="ID de la cuenta por pagar asociada",
    )
    fecha_emision: datetime = Field(
        ...,
        description="Fecha de emisión de la retención",
    )
    # Retención de IVA
    base_imponible_iva: Decimal = Field(
        ...,
        ge=0,
        description="Base imponible para retención de IVA",
    )
    retencion_iva_codigo: str = Field(
        ...,
        max_length=2,
        description="Código de retención de IVA según Tabla 19 del SRI",
    )
    retencion_iva_porcentaje: Decimal = Field(
        ...,
        ge=0,
        description="Porcentaje de retención de IVA",
    )
    # Retención de Renta
    base_imponible_renta: Decimal = Field(
        ...,
        ge=0,
        description="Base imponible para retención de Renta",
    )
    retencion_renta_codigo: str = Field(
        ...,
        max_length=3,
        description="Código de retención de Renta según Tabla 20 del SRI",
    )
    retencion_renta_porcentaje: Decimal = Field(
        ...,
        ge=0,
        description="Porcentaje de retención de Renta",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales",
    )


class RetencionCompraUpdate(BaseModel):
    """Esquema para actualizar una retención de compra"""
    estado: str | None = Field(
        None,
        max_length=20,
        description="Estado: borrador, firmado, enviado, autorizado, rechazado",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales",
    )


class RetencionCompraResponse(BaseModel):
    """Esquema de respuesta para una retención de compra"""
    id: UUID = Field(..., description="ID único de la retención")
    company_id: UUID = Field(..., description="ID de la empresa")
    supplier_id: UUID = Field(..., description="ID del proveedor")
    user_id: UUID = Field(..., description="ID del usuario")
    comprobante_id: UUID | None = Field(None, description="ID del comprobante de retención")
    cuenta_por_pagar_id: UUID | None = Field(None, description="ID de la cuenta por pagar")
    numero_retencion: str | None = Field(None, description="Número de retención")
    fecha_emision: datetime = Field(..., description="Fecha de emisión")
    base_imponible_iva: Decimal = Field(..., description="Base imponible IVA")
    retencion_iva_codigo: str = Field(..., description="Código retención IVA")
    retencion_iva_porcentaje: Decimal = Field(..., description="% retención IVA")
    retencion_iva_valor: Decimal = Field(..., description="Valor retención IVA")
    base_imponible_renta: Decimal = Field(..., description="Base imponible Renta")
    retencion_renta_codigo: str = Field(..., description="Código retención Renta")
    retencion_renta_porcentaje: Decimal = Field(..., description="% retención Renta")
    retencion_renta_valor: Decimal = Field(..., description="Valor retención Renta")
    estado: str = Field(..., description="Estado")
    observaciones: str | None = Field(None, description="Observaciones")
    is_active: bool = Field(..., description="Está activa")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

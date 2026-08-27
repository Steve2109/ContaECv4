"""
ContaEC - Esquemas Pydantic de Punto de Venta (POS)
Schemas para sesiones de caja, tickets, detalles y arqueos
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================
# Sesión de Caja (POSCashSession)
# ==========================================

class POSCashSessionCreate(BaseModel):
    """Esquema para abrir una nueva sesión de caja"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    warehouse_id: str | None = Field(
        None,
        description="ID del almacén desde el que vende el POS",
    )
    numero_caja: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Número de caja (ej: CAJA-001)",
        examples=["CAJA-001"],
    )
    monto_apertura: Decimal = Field(
        ...,
        ge=0,
        description="Monto inicial de efectivo al abrir la caja",
        examples=["200.00"],
    )


class POSCashSessionClose(BaseModel):
    """Esquema para cerrar una sesión de caja"""
    monto_cierre_efectivo: Decimal = Field(
        ...,
        ge=0,
        description="Efectivo contado al cerrar la caja",
    )
    observaciones_cierre: str | None = Field(
        None,
        description="Observaciones al cerrar la caja",
    )


class POSCashSessionResponse(BaseModel):
    """Esquema de respuesta para una sesión de caja"""
    id: UUID = Field(..., description="ID único de la sesión")
    company_id: UUID = Field(..., description="ID de la empresa")
    warehouse_id: UUID | None = Field(None, description="ID del almacén")
    numero_caja: str = Field(..., description="Número de caja")
    user_id: UUID = Field(..., description="ID del cajero")
    estado: str = Field(..., description="Estado: abierta, cerrada")
    fecha_apertura: datetime = Field(..., description="Fecha de apertura")
    fecha_cierre: datetime | None = Field(None, description="Fecha de cierre")
    monto_apertura: Decimal = Field(..., description="Monto de apertura")
    monto_cierre_efectivo: Decimal | None = Field(None, description="Efectivo contado al cierre")
    monto_cierre_calculado: Decimal | None = Field(None, description="Efectivo calculado al cierre")
    monto_diferencia: Decimal | None = Field(None, description="Diferencia (sobrante/faltante)")
    total_ventas_efectivo: Decimal = Field(..., description="Total ventas efectivo")
    total_ventas_tarjeta: Decimal = Field(..., description="Total ventas tarjeta")
    total_ventas_credito: Decimal = Field(..., description="Total ventas crédito")
    total_ventas_otro: Decimal = Field(..., description="Total ventas otro")
    total_ventas: Decimal = Field(..., description="Total general ventas")
    total_propina: Decimal = Field(..., description="Total propinas")
    total_descuentos: Decimal = Field(..., description="Total descuentos")
    total_devoluciones: Decimal = Field(..., description="Total devoluciones")
    observaciones_cierre: str | None = Field(None, description="Observaciones de cierre")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class POSCashSessionResumen(BaseModel):
    """Esquema de resumen de sesión de caja para arqueo"""
    id: UUID = Field(..., description="ID único de la sesión")
    numero_caja: str = Field(..., description="Número de caja")
    estado: str = Field(..., description="Estado de la sesión")
    fecha_apertura: datetime = Field(..., description="Fecha de apertura")
    monto_apertura: Decimal = Field(..., description="Monto de apertura")
    total_ventas_efectivo: Decimal = Field(..., description="Total ventas efectivo")
    total_ventas_tarjeta: Decimal = Field(..., description="Total ventas tarjeta")
    total_ventas_credito: Decimal = Field(..., description="Total ventas crédito")
    total_ventas_otro: Decimal = Field(..., description="Total ventas otro")
    total_ventas: Decimal = Field(..., description="Total general ventas")
    total_propina: Decimal = Field(..., description="Total propinas")
    total_descuentos: Decimal = Field(..., description="Total descuentos")
    total_devoluciones: Decimal = Field(..., description="Total devoluciones")
    efectivo_esperado: Decimal = Field(..., description="Efectivo esperado (apertura + ventas_efectivo - devoluciones)")
    cantidad_tickets: int = Field(..., description="Cantidad de tickets")
    cantidad_tickets_pagados: int = Field(..., description="Cantidad de tickets pagados")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Ticket POS (POSTicket)
# ==========================================

class POSTicketDetalleCreate(BaseModel):
    """Esquema para crear una línea de detalle de ticket"""
    product_id: str | None = Field(
        None,
        description="ID del producto (opcional para items manuales)",
    )
    codigo_principal: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Código principal del producto",
        examples=["PROD001"],
    )
    descripcion: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Descripción del producto o servicio",
    )
    cantidad: Decimal = Field(
        ...,
        gt=0,
        description="Cantidad vendida",
    )
    unidad_medida: str = Field(
        default="Unidad",
        max_length=50,
        description="Unidad de medida",
    )
    precio_unitario: Decimal = Field(
        ...,
        ge=0,
        description="Precio unitario sin impuestos",
    )
    descuento: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Descuento aplicado",
    )
    iva_codigo: str = Field(
        ...,
        max_length=2,
        description="Código de tarifa de IVA según Tabla 16 del SRI",
        examples=["2"],
    )
    iva_porcentaje: Decimal = Field(
        ...,
        ge=0,
        description="Porcentaje de IVA",
        examples=["0.00"],
    )


class POSTicketDetalleResponse(BaseModel):
    """Esquema de respuesta para una línea de detalle de ticket"""
    id: UUID = Field(..., description="ID único del detalle")
    ticket_id: UUID = Field(..., description="ID del ticket")
    product_id: UUID | None = Field(None, description="ID del producto")
    codigo_principal: str = Field(..., description="Código principal")
    descripcion: str = Field(..., description="Descripción")
    cantidad: Decimal = Field(..., description="Cantidad")
    unidad_medida: str = Field(..., description="Unidad de medida")
    precio_unitario: Decimal = Field(..., description="Precio unitario")
    descuento: Decimal = Field(..., description="Descuento")
    precio_total_sin_impuestos: Decimal = Field(..., description="Precio total sin impuestos")
    iva_codigo: str = Field(..., description="Código IVA")
    iva_porcentaje: Decimal = Field(..., description="% IVA")
    iva_valor: Decimal = Field(..., description="Valor IVA")
    created_at: datetime = Field(..., description="Fecha de creación")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class POSTicketCreate(BaseModel):
    """Esquema para crear un nuevo ticket de venta POS"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    cash_session_id: str = Field(
        ...,
        description="ID de la sesión de caja",
    )
    tipo_venta: str = Field(
        default="efectivo",
        max_length=20,
        description="Tipo de venta: efectivo, tarjeta, credito, mixto, otro",
    )
    cliente_nombre: str | None = Field(
        None,
        max_length=200,
        description="Nombre del cliente (default: CONSUMIDOR FINAL)",
    )
    cliente_identificacion: str | None = Field(
        None,
        max_length=20,
        description="Número de identificación del cliente (default: 9999999999999)",
    )
    cliente_tipo_identificacion: str | None = Field(
        None,
        max_length=2,
        description="Tipo de identificación (default: 07=consumidor final)",
    )
    cliente_direccion: str | None = Field(
        None,
        max_length=300,
        description="Dirección del cliente",
    )
    cliente_telefono: str | None = Field(
        None,
        max_length=30,
        description="Teléfono del cliente",
    )
    cliente_email: str | None = Field(
        None,
        max_length=255,
        description="Correo electrónico del cliente",
    )
    detalles: list[POSTicketDetalleCreate] = Field(
        ...,
        min_length=1,
        description="Lista de líneas de detalle",
    )
    monto_efectivo: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Monto pagado en efectivo",
    )
    monto_tarjeta: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Monto pagado con tarjeta",
    )
    monto_credito: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Monto a crédito",
    )
    monto_otro: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Monto pagado con otra forma de pago",
    )
    propina: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Propina del cliente",
    )
    numero_tarjeta: str | None = Field(
        None,
        max_length=4,
        description="Últimos 4 dígitos de la tarjeta",
    )
    tarjeta_tipo: str | None = Field(
        None,
        max_length=20,
        description="Tipo de tarjeta: debito o credito",
    )
    tarjeta_marca: str | None = Field(
        None,
        max_length=30,
        description="Marca de la tarjeta: visa, mastercard, amex, diners, discover, otra",
    )
    tarjeta_banco: str | None = Field(
        None,
        max_length=100,
        description="Banco emisor de la tarjeta",
    )
    tarjeta_titular: str | None = Field(
        None,
        max_length=200,
        description="Nombre del titular de la tarjeta",
    )
    referencia_pago: str | None = Field(
        None,
        max_length=100,
        description="Referencia del pago",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales",
    )
    crear_comprobante: bool = Field(
        default=False,
        description="Si es True, se crea automáticamente un comprobante (factura) electrónico",
    )


class POSTicketResponse(BaseModel):
    """Esquema de respuesta para un ticket POS"""
    id: UUID = Field(..., description="ID único del ticket")
    company_id: UUID = Field(..., description="ID de la empresa")
    cash_session_id: UUID = Field(..., description="ID de la sesión de caja")
    comprobante_id: UUID | None = Field(None, description="ID del comprobante electrónico")
    numero_ticket: str = Field(..., description="Número de ticket")
    estado: str = Field(..., description="Estado: pendiente, pagado, anulado, devuelto")
    tipo_venta: str = Field(..., description="Tipo de venta")
    cliente_nombre: str = Field(..., description="Nombre del cliente")
    cliente_identificacion: str = Field(..., description="Identificación del cliente")
    cliente_tipo_identificacion: str = Field(..., description="Tipo de identificación")
    cliente_direccion: str | None = Field(None, description="Dirección del cliente")
    cliente_telefono: str | None = Field(None, description="Teléfono del cliente")
    cliente_email: str | None = Field(None, description="Correo electrónico del cliente")
    subtotal_sin_impuestos: Decimal = Field(..., description="Subtotal sin impuestos")
    total_iva: Decimal = Field(..., description="Total IVA")
    total_descuento: Decimal = Field(..., description="Total descuentos")
    total_con_impuestos: Decimal = Field(..., description="Total con impuestos")
    monto_efectivo: Decimal = Field(..., description="Monto efectivo")
    monto_tarjeta: Decimal = Field(..., description="Monto tarjeta")
    monto_credito: Decimal = Field(..., description="Monto crédito")
    monto_otro: Decimal = Field(..., description="Monto otro")
    cambio: Decimal = Field(..., description="Cambio devuelto")
    propina: Decimal = Field(..., description="Propina")
    numero_tarjeta: str | None = Field(None, description="Últimos 4 dígitos tarjeta")
    tarjeta_tipo: str | None = Field(None, description="Tipo de tarjeta (debito/credito)")
    tarjeta_marca: str | None = Field(None, description="Marca de la tarjeta")
    tarjeta_banco: str | None = Field(None, description="Banco emisor")
    tarjeta_titular: str | None = Field(None, description="Titular de la tarjeta")
    referencia_pago: str | None = Field(None, description="Referencia de pago")
    observaciones: str | None = Field(None, description="Observaciones")
    user_id: UUID = Field(..., description="ID del cajero")
    detalles: list[POSTicketDetalleResponse] = Field(
        default_factory=list,
        description="Líneas de detalle",
    )
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Arqueo de Caja (POSArqueo)
# ==========================================

class POSArqueoCreate(BaseModel):
    """Esquema para crear un arqueo de caja"""
    tipo: str = Field(
        default="parcial",
        max_length=20,
        description="Tipo de arqueo: parcial, final",
    )
    billetes: dict[str, int] | None = Field(
        None,
        description="Conteo de billetes por denominación: {\"1\": 5, \"5\": 10, ...}",
    )
    monedas: dict[str, int] | None = Field(
        None,
        description="Conteo de monedas por denominación: {\"0.05\": 20, \"0.10\": 50, ...}",
    )
    total_billetes: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Total en billetes",
    )
    total_monedas: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Total en monedas",
    )
    total_efectivo_contado: Decimal = Field(
        ...,
        ge=0,
        description="Total de efectivo contado",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones del arqueo",
    )

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str) -> str:
        """Valida que el tipo de arqueo sea válido"""
        if v not in ("parcial", "final"):
            raise ValueError("Tipo de arqueo inválido. Válidos: parcial, final")
        return v


class POSArqueoResponse(BaseModel):
    """Esquema de respuesta para un arqueo de caja"""
    id: UUID = Field(..., description="ID único del arqueo")
    cash_session_id: UUID = Field(..., description="ID de la sesión de caja")
    company_id: UUID = Field(..., description="ID de la empresa")
    tipo: str = Field(..., description="Tipo de arqueo: parcial, final")
    billetes: str | None = Field(None, description="JSON conteo de billetes")
    monedas: str | None = Field(None, description="JSON conteo de monedas")
    total_billetes: Decimal = Field(..., description="Total billetes")
    total_monedas: Decimal = Field(..., description="Total monedas")
    total_efectivo_contado: Decimal = Field(..., description="Total efectivo contado")
    total_efectivo_calculado: Decimal = Field(..., description="Total efectivo calculado")
    diferencia: Decimal = Field(..., description="Diferencia (sobrante+/faltante-)")
    observaciones: str | None = Field(None, description="Observaciones")
    user_id: UUID = Field(..., description="ID del usuario")
    created_at: datetime = Field(..., description="Fecha de creación")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class POSArqueoCerrarRequest(BaseModel):
    """Esquema para cerrar un arqueo con desglose de denominaciones"""
    billetes_100: int = Field(default=0, ge=0, description="Cantidad de billetes de $100")
    billetes_50: int = Field(default=0, ge=0, description="Cantidad de billetes de $50")
    billetes_20: int = Field(default=0, ge=0, description="Cantidad de billetes de $20")
    billetes_10: int = Field(default=0, ge=0, description="Cantidad de billetes de $10")
    billetes_5: int = Field(default=0, ge=0, description="Cantidad de billetes de $5")
    billetes_1: int = Field(default=0, ge=0, description="Cantidad de billetes de $1")
    monedas: Decimal = Field(default=Decimal("0"), ge=0, description="Total en monedas")
    vales: Decimal = Field(default=Decimal("0"), ge=0, description="Total en vales")
    vouchers: Decimal = Field(default=Decimal("0"), ge=0, description="Total en vouchers/tarjetas")
    umbral_diferencia: Decimal = Field(
        default=Decimal("5.00"),
        ge=0,
        description="Umbral para flag de diferencia (default $5.00)",
    )
    observaciones: str | None = Field(None, description="Observaciones del cierre")


class POSArqueoCerrarResponse(BaseModel):
    """Esquema de respuesta tras cerrar un arqueo"""
    id: UUID = Field(..., description="ID único del arqueo")
    tipo: str = Field(..., description="Tipo de arqueo")
    total_efectivo_sistema: Decimal = Field(..., description="Efectivo esperado por el sistema")
    total_efectivo_real: Decimal = Field(..., description="Efectivo real contado")
    diferencia: Decimal = Field(..., description="Diferencia (sobrante+/faltante-)")
    estado_diferencia: str = Field(..., description="OK, CON_DIFERENCIA")
    detalle_billetes: dict[str, int] = Field(..., description="Desglose de billetes")
    total_monedas: Decimal = Field(..., description="Total en monedas")
    total_vales: Decimal = Field(..., description="Total en vales")
    total_vouchers: Decimal = Field(..., description="Total en vouchers")
    observaciones: str | None = Field(None, description="Observaciones")
    created_at: datetime = Field(..., description="Fecha de creación")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class POSArqueoResumenItem(BaseModel):
    """Esquema de un item en el resumen de arqueos"""
    id: UUID = Field(..., description="ID del arqueo")
    numero_caja: str = Field(..., description="Número de caja")
    tipo: str = Field(..., description="Tipo: parcial, final")
    fecha_apertura: datetime = Field(..., description="Fecha apertura sesión")
    fecha_arqueo: datetime = Field(..., description="Fecha del arqueo")
    total_efectivo_sistema: Decimal = Field(..., description="Efectivo esperado")
    total_efectivo_contado: Decimal = Field(..., description="Efectivo contado")
    diferencia: Decimal = Field(..., description="Diferencia")
    estado_diferencia: str | None = Field(None, description="OK, CON_DIFERENCIA, o None")
    cajero_email: str | None = Field(None, description="Email del cajero")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class POSArqueoResumenResponse(BaseModel):
    """Esquema de respuesta para resumen de arqueos"""
    total_registros: int = Field(..., description="Total de registros")
    total_sobrante: Decimal = Field(..., description="Suma de diferencias positivas")
    total_faltante: Decimal = Field(..., description="Suma de diferencias negativas (valor absoluto)")
    total_diferencia_neta: Decimal = Field(..., description="Diferencia neta (sobrante - faltante)")
    arqueos: list[POSArqueoResumenItem] = Field(..., description="Lista de arqueos")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class POSArqueoReporteResponse(BaseModel):
    """Esquema de respuesta para reporte de arqueo"""
    id: UUID = Field(..., description="ID del arqueo")
    tipo: str = Field(..., description="Tipo de arqueo")
    numero_caja: str = Field(..., description="Número de caja")
    fecha_apertura: datetime = Field(..., description="Fecha apertura")
    fecha_arqueo: datetime = Field(..., description="Fecha arqueo")
    cajero: str = Field(..., description="Nombre del cajero")
    monto_apertura: Decimal = Field(..., description="Monto apertura")
    total_ventas_efectivo: Decimal = Field(..., description="Total ventas efectivo")
    total_ventas_tarjeta: Decimal = Field(..., description="Total ventas tarjeta")
    total_ventas_credito: Decimal = Field(..., description="Total ventas crédito")
    total_ventas: Decimal = Field(..., description="Total ventas general")
    total_efectivo_sistema: Decimal = Field(..., description="Efectivo esperado")
    detalle_billetes: dict[str, int] | None = Field(None, description="Billetes contados")
    total_monedas: Decimal = Field(..., description="Total monedas")
    total_vales: Decimal = Field(..., description="Total vales")
    total_vouchers: Decimal = Field(..., description="Total vouchers")
    total_efectivo_real: Decimal = Field(..., description="Efectivo real contado")
    diferencia: Decimal = Field(..., description="Diferencia")
    estado_diferencia: str | None = Field(None)
    observaciones: str | None = Field(None)

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Búsqueda de producto por código de barras
# ==========================================

class POSProductSearchResponse(BaseModel):
    """Esquema de respuesta para búsqueda de producto por código de barras"""
    id: UUID = Field(..., description="ID del producto")
    codigo_principal: str = Field(..., description="Código principal")
    codigo_barras: str | None = Field(None, description="Código de barras")
    descripcion: str = Field(..., description="Descripción del producto")
    tipo: str = Field(..., description="Tipo: B=Bien, S=Servicio")
    precio_unitario: Decimal = Field(..., description="Precio unitario sin impuestos")
    iva_codigo: str = Field(..., description="Código IVA")
    iva_porcentaje: Decimal = Field(..., description="% IVA")
    unidad_medida: str = Field(..., description="Unidad de medida")
    stock: Decimal = Field(..., description="Stock actual")
    stock_minimo: Decimal = Field(..., description="Stock mínimo")
    iva_incluido: bool | None = Field(None, description="Indica si el IVA está incluido en el precio")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Ticket imprimible (formato recibos)
# ==========================================

class POSTicketPrintResponse(BaseModel):
    """Esquema de respuesta para datos de impresión de ticket"""
    numero_ticket: str = Field(..., description="Número de ticket")
    fecha: datetime = Field(..., description="Fecha del ticket")
    cliente_nombre: str = Field(..., description="Nombre del cliente")
    cliente_identificacion: str = Field(..., description="Identificación del cliente")
    cajero: str = Field(..., description="Nombre del cajero")
    numero_caja: str = Field(..., description="Número de caja")
    items: list[dict] = Field(..., description="Lista de items del ticket")
    subtotal_sin_impuestos: Decimal = Field(..., description="Subtotal sin impuestos")
    total_iva: Decimal = Field(..., description="Total IVA")
    total_descuento: Decimal = Field(..., description="Total descuentos")
    total_con_impuestos: Decimal = Field(..., description="Total con impuestos")
    monto_efectivo: Decimal = Field(..., description="Efectivo recibido")
    monto_tarjeta: Decimal = Field(..., description="Monto con tarjeta")
    monto_credito: Decimal = Field(..., description="Monto a crédito")
    monto_otro: Decimal = Field(..., description="Monto otro")
    cambio: Decimal = Field(..., description="Cambio")
    propina: Decimal = Field(..., description="Propina")
    tipo_venta: str = Field(..., description="Tipo de venta")
    cliente_direccion: str | None = Field(None, description="Dirección del cliente")
    cliente_telefono: str | None = Field(None, description="Teléfono del cliente")
    cliente_email: str | None = Field(None, description="Correo del cliente")
    numero_tarjeta: str | None = Field(None, description="Últimos 4 dígitos de la tarjeta")
    tarjeta_tipo: str | None = Field(None, description="Tipo de tarjeta (debito/credito)")
    tarjeta_marca: str | None = Field(None, description="Marca de la tarjeta")
    tarjeta_banco: str | None = Field(None, description="Banco emisor")
    tarjeta_titular: str | None = Field(None, description="Titular de la tarjeta")
    empresa_nombre: str | None = Field(None, description="Nombre de la empresa")
    empresa_ruc: str | None = Field(None, description="RUC de la empresa")
    empresa_direccion: str | None = Field(None, description="Dirección de la empresa")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

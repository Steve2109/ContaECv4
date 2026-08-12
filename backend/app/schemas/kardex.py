"""
ContaEC - Esquemas Pydantic de Kardex (Movimientos de Inventario)
Schemas para creación, ajuste, respuesta y listado de movimientos de kardex
con cálculo automático de saldos
"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KardexCreate(BaseModel):
    """Esquema para crear un movimiento de kardex"""
    company_id: str = Field(
        ...,
        description="ID de la empresa a la que pertenece el movimiento",
    )
    product_id: str = Field(
        ...,
        description="ID del producto al que pertenece el movimiento",
    )
    tipo_movimiento: str = Field(
        ...,
        description="Tipo de movimiento: entrada, salida, ajuste",
        examples=["entrada"],
    )
    cantidad: Decimal = Field(
        ...,
        gt=0,
        description="Cantidad del movimiento (siempre positiva)",
        examples=["10.0000"],
    )
    costo_unitario: Decimal = Field(
        ...,
        ge=0,
        description="Costo unitario del producto",
        examples=["15.50"],
    )
    referencia_tipo: str | None = Field(
        None,
        max_length=50,
        description="Tipo de documento de referencia: comprobante, ajuste, compra",
    )
    referencia_id: str | None = Field(
        None,
        max_length=36,
        description="ID del documento de referencia",
    )
    referencia_secuencial: str | None = Field(
        None,
        max_length=20,
        description="Número secuencial del documento de referencia",
    )
    detalle: str | None = Field(
        None,
        max_length=500,
        description="Descripción del movimiento",
    )
    fecha_movimiento: datetime | None = Field(
        None,
        description="Fecha y hora del movimiento (default: ahora)",
    )

    @field_validator("tipo_movimiento")
    @classmethod
    def validate_tipo_movimiento(cls, v: str) -> str:
        """Valida que el tipo de movimiento sea válido"""
        validos = {"entrada", "salida", "ajuste"}
        if v not in validos:
            raise ValueError(
                f"Tipo de movimiento inválido: {v}. "
                f"Válidos: entrada, salida, ajuste"
            )
        return v


class KardexAjuste(BaseModel):
    """Esquema para crear un ajuste de inventario"""
    company_id: str = Field(
        ...,
        description="ID de la empresa",
    )
    product_id: str = Field(
        ...,
        description="ID del producto a ajustar",
    )
    cantidad_ajuste: Decimal = Field(
        ...,
        description="Cantidad del ajuste (positivo para incrementar, negativo para decrementar)",
        examples=["5.0000"],
    )
    costo_unitario: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Costo unitario para el ajuste (0 para ajustes sin costo)",
    )
    detalle: str | None = Field(
        None,
        max_length=500,
        description="Motivo del ajuste",
    )
    referencia_tipo: str | None = Field(
        None,
        max_length=50,
        description="Tipo de referencia del ajuste",
    )
    referencia_id: str | None = Field(
        None,
        max_length=36,
        description="ID del documento de referencia",
    )

    @field_validator("cantidad_ajuste")
    @classmethod
    def validate_cantidad_ajuste(cls, v: Decimal) -> Decimal:
        """Valida que la cantidad de ajuste no sea cero"""
        if v == 0:
            raise ValueError("La cantidad de ajuste no puede ser cero")
        return v


class KardexResponse(BaseModel):
    """Esquema de respuesta para un movimiento de kardex"""
    id: UUID = Field(..., description="ID único del movimiento")
    company_id: UUID = Field(..., description="ID de la empresa")
    product_id: UUID = Field(..., description="ID del producto")
    warehouse_id: UUID | None = Field(None, description="ID del almacén asociado")
    tipo_movimiento: str = Field(..., description="Tipo de movimiento")
    cantidad: Decimal = Field(..., description="Cantidad del movimiento")
    costo_unitario: Decimal = Field(..., description="Costo unitario")
    costo_total: Decimal = Field(..., description="Costo total del movimiento")
    saldo_cantidad: Decimal = Field(..., description="Saldo de cantidad acumulado")
    saldo_valor: Decimal = Field(..., description="Saldo de valor acumulado")
    referencia_tipo: str | None = Field(None, description="Tipo de referencia")
    referencia_id: UUID | None = Field(None, description="ID de referencia")
    referencia_secuencial: str | None = Field(None, description="Secuencial de referencia")
    detalle: str | None = Field(None, description="Detalle del movimiento")
    fecha_movimiento: datetime = Field(..., description="Fecha del movimiento")
    user_id: UUID = Field(..., description="ID del usuario")
    is_active: bool = Field(..., description="Indica si está activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class KardexSaldoResponse(BaseModel):
    """Esquema de respuesta para el saldo actual de un producto"""
    product_id: UUID = Field(..., description="ID del producto")
    saldo_cantidad: Decimal = Field(default=Decimal("0"), description="Cantidad actual en stock")
    saldo_valor: Decimal = Field(default=Decimal("0"), description="Valor actual en stock")
    costo_promedio: Decimal = Field(default=Decimal("0"), description="Costo promedio ponderado")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class KardexReporteResponse(BaseModel):
    """Esquema de respuesta para el reporte de kardex"""
    product_id: str = Field(..., description="ID del producto")
    producto_descripcion: str = Field(..., description="Descripción del producto")
    producto_codigo: str = Field(..., description="Código principal del producto")
    metodo_valoracion: str = Field(..., description="Método de valoración utilizado")
    movimientos: list[KardexResponse] = Field(
        default_factory=list,
        description="Lista de movimientos del período",
    )
    saldo_inicial_cantidad: Decimal = Field(default=Decimal("0"), description="Saldo inicial cantidad")
    saldo_inicial_valor: Decimal = Field(default=Decimal("0"), description="Saldo inicial valor")
    total_entradas_cantidad: Decimal = Field(default=Decimal("0"), description="Total entradas cantidad")
    total_entradas_valor: Decimal = Field(default=Decimal("0"), description="Total entradas valor")
    total_salidas_cantidad: Decimal = Field(default=Decimal("0"), description="Total salidas cantidad")
    total_salidas_valor: Decimal = Field(default=Decimal("0"), description="Total salidas valor")
    saldo_final_cantidad: Decimal = Field(default=Decimal("0"), description="Saldo final cantidad")
    saldo_final_valor: Decimal = Field(default=Decimal("0"), description="Saldo final valor")
